# Veilig gebruik van Home Invest via Home Assistant en een domein

Home Invest kan uitsluitend lokaal via Home Assistant-ingress worden gebruikt. Het installeren van Home Invest op een host die via internet bereikbaar is, betekent **niet automatisch** dat Home Invest zelf veilig publiek toegankelijk is. Controleer alle onderstaande stappen voordat je toegang van buiten je thuisnetwerk toestaat.

## Aanbevolen inrichting

1. Gebruik waar mogelijk een vertrouwde VPN (bijvoorbeeld WireGuard/Tailscale), en houd Home Invest via Home Assistant-ingress achter authenticatie.
2. Gebruik HTTPS met een geldig certificaat en configureer proxy headers alleen van vertrouwde proxy-adressen. Publiceer **geen** SQLite-bestanden, app-data, back-upmappen of config/secrets.
3. De extra sensor-API op `8100/tcp` staat standaard **niet** open op de host (`null` in `portfolio/config.yaml`). Zet deze alleen aan als deze nodig is. Gebruik dan een lange unieke `home_assistant_token`; zet de poort niet rechtstreeks op internet.
4. Bewaar tokens en back-ups buiten webtoegankelijke paden, bescherm bestandsrechten en controleer herstelprocedures.
5. Houd Home Assistant OS/Supervisor, proxy en Home Invest up-to-date. Controleer loginpogingen en onverwachte port-forwarding.

## Wat de nieuwe regressietest wel en niet doet

`tests/test_security_configuration.py` verhindert dat enkele beveiligingsgevoelige defaults (ingress, sensorpoort, tokenoptie, algemene DB-poorten) ongemerkt gewijzigd worden.

**Dit bewijst geen veilige internetdeployment** en test geen sessies, CSRF, autorisatie, encryptie, headers of proxyconfiguratie. Daarvoor staan audits en integratietests op de roadmap. Meld kwetsbaarheden niet met echte tokens of persoonsgegevens in publieke Issues.

## Volgende controles (fase 9 en 14)

- Alle API- en objectroutes nalopen op toegang en scheiding tussen gebruikers.
- Sessie-/passkeybeveiliging en rate limiting nagaan.
- Relevante CSP, XSS, CSRF, uploadvalidatie en HTTP-securityheaders testen.
- Back-updownloads, applicatielogs en tokenrotatie toetsen.
- Echte Home Assistant Supervisor-installatie en reverse proxy testen.
