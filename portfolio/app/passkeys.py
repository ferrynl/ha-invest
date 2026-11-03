"""WebAuthn passkeys: server-verified challenges, public keys, and one-use ceremonies.

The browser's HTTPS Origin header is the ceremony origin. Registered credentials are
pinned to that exact origin and RP ID; the add-on never trusts an origin supplied in JSON.
Home Assistant ingress remains the outer authorization boundary.
"""
import hashlib
import json
import re
import secrets
import time
from urllib.parse import urlsplit

from webauthn import (
    base64url_to_bytes, generate_authentication_options,
    generate_registration_options, options_to_json,
    verify_authentication_response, verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
    ResidentKeyRequirement, UserVerificationRequirement,
)

CHALLENGE_TTL = 180
MAX_PASSKEYS = 10


def ceremony_origin(header):
    """Reject HTTP on public hosts, unusual origins, credentials, and ambiguities."""
    if not isinstance(header, str) or len(header) > 300:
        raise ValueError("Passkeys vereisen een veilige HTTPS-verbinding.")
    try:
        url = urlsplit(header)
        host = url.hostname
        if (not host or url.username or url.password or url.path or url.query
                or url.fragment or host.endswith('.') or not re.fullmatch(r'[a-zA-Z0-9.:-]{1,253}', host)):
            raise ValueError()
        if url.scheme == 'https' and url.port in (None, 443):
            return 'https://' + host.lower(), host.lower()
        if url.scheme == 'http' and host == 'localhost' and url.port is not None:
            return f'http://localhost:{url.port}', 'localhost'
    except (ValueError, TypeError):
        pass
    raise ValueError("Passkeys werken alleen via HTTPS (of localhost voor ontwikkeling).")


def _new_challenge(store, kind, origin, rp_id, user_id=None, session_token=''):
    challenge = secrets.token_bytes(32)
    ceremony_id = secrets.token_urlsafe(24)
    with store.connect() as db:
        db.execute('DELETE FROM passkey_challenges WHERE expires_at < ?', (time.time(),))
        if db.execute('SELECT COUNT(*) FROM passkey_challenges').fetchone()[0] >= 200:
            raise ValueError('Te veel passkey-aanvragen. Probeer het later opnieuw.')
        db.execute(
            'INSERT INTO passkey_challenges (id,kind,challenge,origin,rp_id,user_id,session_hash,expires_at) VALUES (?,?,?,?,?,?,?,?)',
            (ceremony_id,kind,challenge,origin,rp_id,user_id,
             hashlib.sha256(session_token.encode()).hexdigest() if session_token else '',
             time.time() + CHALLENGE_TTL),
        )
    return ceremony_id, challenge


def _consume(store, ceremony_id, kind, session_token=''):
    if not isinstance(ceremony_id, str) or len(ceremony_id) > 100:
        raise ValueError('Passkey-aanvraag verlopen. Probeer opnieuw.')
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        entry = db.execute('SELECT * FROM passkey_challenges WHERE id=? AND kind=?',
                           (ceremony_id, kind)).fetchone()
        db.execute('DELETE FROM passkey_challenges WHERE id=?', (ceremony_id,))
    if (not entry or entry['expires_at'] < time.time()
            or (kind == 'register' and
                not secrets.compare_digest(entry['session_hash'],
                                            hashlib.sha256(session_token.encode()).hexdigest()))):
        raise ValueError('Passkey-aanvraag verlopen. Probeer opnieuw.')
    return entry


def list_keys(store, user):
    if not user or user['id'] is None:
        raise ValueError('Meld je aan met je eigen gebruikersaccount.')
    with store.read() as db:
        rows = db.execute('SELECT id,label,created_at,last_used_at,origin FROM passkeys WHERE user_id=? ORDER BY id',
                          (user['id'],)).fetchall()
    return {'passkeys': [dict(row) for row in rows]}


def begin_registration(store, user, session_token, password, origin_header):
    if not user or user['id'] is None:
        raise ValueError('Meld je aan voordat je een passkey toevoegt.')
    from security import verify_password
    with store.read() as db:
        account = db.execute('SELECT password_hash,active,revision,username FROM users WHERE id=?',
                             (user['id'],)).fetchone()
        count = db.execute('SELECT COUNT(*) FROM passkeys WHERE user_id=?',
                           (user['id'],)).fetchone()[0]
        existing = db.execute('SELECT credential_id FROM passkeys WHERE user_id=?',
                              (user['id'],)).fetchall()
    if not account or not account['active'] or not verify_password(password, account['password_hash']):
        raise ValueError('Huidig wachtwoord onjuist.')
    if count >= MAX_PASSKEYS:
        raise ValueError('Maximaal tien passkeys per account.')
    origin, rp_id = ceremony_origin(origin_header)
    key, challenge = _new_challenge(store, 'register', origin, rp_id, user['id'], session_token)
    options = generate_registration_options(
        rp_id=rp_id, rp_name='Home Invest', user_name=account['username'],
        user_id=hashlib.sha256(f'home-invest:{user["id"]}'.encode()).digest(),
        challenge=challenge,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=row['credential_id'])
                             for row in existing],
    )
    return {'ceremony_id': key, 'options': json.loads(options_to_json(options))}


def finish_registration(store, user, session_token, ceremony_id, credential, label):
    if not user or user['id'] is None:
        raise ValueError('Meld je eerst aan.')
    entry = _consume(store, ceremony_id, 'register', session_token)
    if user['id'] != entry['user_id']:
        raise ValueError('Passkey-aanvraag hoort bij een ander account.')
    if not isinstance(credential, dict):
        raise ValueError('Ongeldige passkey.')
    label = str(label or 'Passkey').strip()[:60] or 'Passkey'
    try:
        checked = verify_registration_response(
            credential=credential, expected_challenge=entry['challenge'],
            expected_origin=entry['origin'], expected_rp_id=entry['rp_id'],
            require_user_verification=True,
        )
    except Exception as error:
        raise ValueError('Passkey-verificatie mislukt.') from error
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        account = db.execute('SELECT active FROM users WHERE id=?', (user['id'],)).fetchone()
        if not account or not account['active']:
            raise ValueError('Account is niet meer actief.')
        if db.execute('SELECT COUNT(*) FROM passkeys WHERE user_id=?', (user['id'],)).fetchone()[0] >= MAX_PASSKEYS:
            raise ValueError('Maximaal tien passkeys per account.')
        try:
            db.execute(
                'INSERT INTO passkeys (user_id,credential_id,public_key,sign_count,origin,rp_id,label,created_at) VALUES (?,?,?,?,?,?,?,?)',
                (user['id'], checked.credential_id, checked.credential_public_key,
                 checked.sign_count, entry['origin'], entry['rp_id'], label, time.time()),
            )
        except Exception as error:
            if type(error).__name__ == 'IntegrityError':
                raise ValueError('Deze passkey is al geregistreerd.') from error
            raise
    return {'ok': True}


def begin_login(store, origin_header):
    origin, rp_id = ceremony_origin(origin_header)
    key, challenge = _new_challenge(store, 'login', origin, rp_id)
    options = generate_authentication_options(
        rp_id=rp_id, challenge=challenge,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return {'ceremony_id': key, 'options': json.loads(options_to_json(options))}


def finish_login(store, auth, ceremony_id, credential):
    entry = _consume(store, ceremony_id, 'login')
    if not isinstance(credential, dict) or not isinstance(credential.get('id'), str):
        raise ValueError('Ongeldige passkey.')
    try:
        credential_id = base64url_to_bytes(credential['id'])
    except Exception as error:
        raise ValueError('Ongeldige passkey.') from error
    with store.read() as db:
        saved = db.execute('''SELECT p.*,u.active,u.revision FROM passkeys p
                              JOIN users u ON u.id=p.user_id
                              WHERE p.credential_id=?''', (credential_id,)).fetchone()
    if not saved or not saved['active'] or not auth.enabled():
        raise ValueError('Passkey niet herkend.')
    if saved['origin'] != entry['origin'] or saved['rp_id'] != entry['rp_id']:
        raise ValueError('Deze passkey hoort bij een ander Home Assistant-adres.')
    try:
        checked = verify_authentication_response(
            credential=credential, expected_challenge=entry['challenge'],
            expected_origin=saved['origin'], expected_rp_id=saved['rp_id'],
            credential_public_key=saved['public_key'],
            credential_current_sign_count=saved['sign_count'],
            require_user_verification=True,
        )
    except Exception as error:
        raise ValueError('Passkey-verificatie mislukt.') from error
    # Compare-and-swap the counter to reject stale, concurrent assertions.
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT p.sign_count,u.active,u.revision FROM passkeys p JOIN users u ON u.id=p.user_id WHERE p.id=?',
                         (saved['id'],)).fetchone()
        if (not row or not row['active'] or row['revision'] != saved['revision']
                or row['sign_count'] != saved['sign_count']):
            raise ValueError('Passkey-aanvraag verlopen. Probeer opnieuw.')
        db.execute('UPDATE passkeys SET sign_count=?,last_used_at=? WHERE id=?',
                   (checked.new_sign_count, time.time(), saved['id']))
    return auth.login_by_id(saved['user_id'])


def delete_key(store, user, key_id, password):
    from security import verify_password
    if not user or user['id'] is None:
        raise ValueError('Meld je aan om passkeys te verwijderen.')
    with store.connect() as db:
        account = db.execute('SELECT password_hash FROM users WHERE id=?', (user['id'],)).fetchone()
        if not account or not verify_password(password, account['password_hash']):
            raise ValueError('Huidig wachtwoord onjuist.')
        if db.execute('DELETE FROM passkeys WHERE id=? AND user_id=?',
                      (int(key_id), user['id'])).rowcount != 1:
            raise ValueError('Passkey niet gevonden.')
    return {'ok': True}
