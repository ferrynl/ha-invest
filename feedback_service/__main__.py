"""Operational commands run inside the Coolify container; no public admin API."""
import argparse
import base64
import os
import signal
import threading
from .store import RelayStore


def github_client():
    from .github import GitHub
    key=os.environ.get('GITHUB_APP_PRIVATE_KEY_FILE','')
    if not key:
        key=base64.b64decode(os.environ['GITHUB_APP_PRIVATE_KEY_B64'],validate=True)
    return GitHub(os.environ['GITHUB_APP_ID'],os.environ['GITHUB_INSTALLATION_ID'],os.environ['GITHUB_REPOSITORY_ID'],key)


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description='Home Invest central feedback service')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('serve')
    invite=commands.add_parser('invite')
    invite.add_argument('--ttl',type=int,default=86400,help='Seconds, 60..604800')
    revoke=commands.add_parser('revoke')
    revoke.add_argument('installation_id')
    ownership=commands.add_parser('owner')
    ownership.add_argument('issue_number',type=int)
    commands.add_parser('status')
    installations=commands.add_parser('installations')
    installations.add_argument('--offset',type=int,default=0)
    installations.add_argument('--limit',type=int,default=100)
    reconcile=commands.add_parser('reconcile')
    reconcile.add_argument('submission_id')
    reconcile.add_argument('issue_number',type=int)
    discard=commands.add_parser('discard')
    discard.add_argument('submission_id')
    args=parser.parse_args()
    store=RelayStore(os.environ.get('FEEDBACK_DATABASE','/data/relay.sqlite3'),os.environ['SERVICE_SECRET'])
    if args.command=='invite':
        print(store.invite(args.ttl))
        return
    if args.command=='revoke':
        store.revoke(args.installation_id)
        print('Installation revoked; queued submissions blocked.')
        return
    if args.command=='owner':
        with store.db() as db:
            row=db.execute('SELECT installation FROM jobs WHERE number=?',(args.issue_number,)).fetchone()
            if not row: raise ValueError('issue_not_found')
        print(row['installation'])
        return
    if args.command=='status':
        with store.db() as db:
            installations=db.execute('SELECT count(*) FROM installations WHERE revoked=0').fetchone()[0]
            states={r['state']:r['count'] for r in db.execute('SELECT state,count(*) AS count FROM jobs GROUP BY state')}
            uncertain=[r['id'] for r in db.execute("SELECT id FROM jobs WHERE state='uncertain' LIMIT 100")]
            oldest=db.execute("SELECT MIN(created) FROM jobs WHERE state='queued'").fetchone()[0]
        print({'active_installations':installations,'submissions':states,'uncertain_ids':uncertain,'oldest_queued_unix':oldest,'github_retry_unix':store.get_meta('github_after',0)})
        return
    if args.command=='installations':
        if not 1<=args.limit<=1000 or args.offset<0: raise ValueError('invalid_page')
        with store.db() as db:
            for row in db.execute('SELECT id,revoked,created FROM installations ORDER BY created,id LIMIT ? OFFSET ?',(args.limit,args.offset)):
                print(dict(row))
        return
    if args.command=='discard':
        with store.db() as db:
            db.execute("UPDATE jobs SET state='blocked',payload='' WHERE id=? AND state='uncertain'",(args.submission_id,))
        print('Uncertain submission discarded; no new GitHub issue created.')
        return
    github=github_client()
    if args.command=='reconcile':
        issue,_=github.request(f'/repos/ferrynl/ha-invest/issues/{args.issue_number}',github.access_token())
        if '<!-- home-invest:'+args.submission_id+' -->' not in issue.get('body','') or issue.get('state') not in ('open','closed'):
            raise ValueError('issue_does_not_match_submission')
        with store.db() as db:
            row=db.execute("SELECT id FROM jobs WHERE id=? AND state='uncertain'",(args.submission_id,)).fetchone()
            if not row: raise ValueError('submission_not_uncertain')
        store.mark(args.submission_id,issue['state'],args.issue_number)
        print('Existing GitHub issue linked; no new issue created.')
        return
    from .github import Worker
    from .server import LimitedServer,make_handler
    # Linux container: prevent concurrent workers during an accidental second
    # replica or overlapping deployment against the same persistent volume.
    import fcntl
    process_lock=open(str(store.path)+'.worker.lock','a')
    fcntl.flock(process_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    secret=os.environ['GITHUB_WEBHOOK_SECRET']
    proxies=tuple(v.strip() for v in os.environ.get('TRUSTED_PROXY_CIDRS','').split(',') if v.strip())
    http=LimitedServer(('0.0.0.0',int(os.environ.get('PORT','8080'))),make_handler(store,secret,github.repository_id,proxies))
    stop=threading.Event()
    worker=threading.Thread(target=Worker(store,github).run,args=(stop,),daemon=True)
    worker.start()
    def shutdown(*_):
        stop.set()
        threading.Thread(target=http.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    try: http.serve_forever()
    finally:
        stop.set()
        http.server_close()
        worker.join(timeout=35)
        process_lock.close()


if __name__=='__main__': main()
