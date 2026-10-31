# Centrale meldservice voor Home Invest — Coolify

Deze container draait apart van de Home Assistant-app. Mensen dienen wensen en bugs in Home Invest in, zonder GitHub-account. Alleen deze centrale dienst bezit de GitHub App-sleutel. De repository staat vast op `ferrynl/ha-invest`.

## In Coolify laden

Gebruik een **Application → Public Repository → Dockerfile** met:

| Instelling | Waarde |
| --- | --- |
| Repository | `https://github.com/ferrynl/ha-invest` |
| Branch | `main` (of de gecontroleerde release `v0.39.0`) |
| Base Directory / buildcontext | `/` |
| Dockerfile Location | `/feedback_service/Dockerfile` |
| Ports Exposes | `8080` |
| Domein | `https://meldingen.home-invest.nl` |
| Persistent Storage | Volume Mount met Destination Path `/data` |
| Health check | `GET /health`, poort `8080` |
| Replicas | **1** |

Maak voor `meldingen.home-invest.nl` een DNS-record naar je VPS. Coolify verzorgt HTTPS. Publiceer poort 8080 niet rechtstreeks op de VPS; verkeer gaat via de HTTPS-proxy. De container luistert intern op `0.0.0.0:8080`.

De Dockerfile gebruikt een eigen gebruiker (UID/GID 10001). Een bind mount moet voor die gebruiker schrijfbaar zijn; een Docker-volume neemt de eigendom van `/data` uit de image over. De bouwcontext sluit portefeuilledata, `.git`, lokale tests, `.env` en sleutelbestanden uit.

**Eén actieve container per volume.** Zet overlappende/rolling deployments uit en stop de oude container vóór een vervanging start. Een procesvergrendeling voorkomt dat twee workers tegelijk hetzelfde volume gebruiken. Gebruik lokale VPS-opslag, geen netwerkbestandssysteem voor SQLite/WAL. Meerdere hosts vereisen later een gedeelde database en een aparte wachtrij; deze eerste uitvoering is een enkele instantie met begrensde gelijktijdigheid.

Zie de officiële [Dockerfile-instructies](https://coolify.io/docs/applications/builds/dockerfile) en [persistente opslag](https://coolify.io/docs/applications/configuration/persistent-storage).

## GitHub App eenmalig instellen

Maak onder jouw GitHub-account een GitHub App, bijvoorbeeld **Home Invest Meldservice**:

1. Homepage: `https://home-invest.nl`.
2. Webhook URL: `https://meldingen.home-invest.nl/v1/github-webhook`.
3. Webhook secret: een eigen willekeurig geheim van minimaal 32 tekens.
4. Repository permissions: **Issues → Read and write**. De verplichte Metadata-leestoegang blijft aan. Geef geen Contents-, Actions-, Administration- of accountrechten.
5. Subscribe to events: **Issues**. Geen OAuth-callback, gebruikersautorisatie of GitHub-login voor melders nodig.
6. Installeer de app uitsluitend op **ferrynl/ha-invest**.
7. Genereer de private PEM-sleutel. Bewaar die in jouw wachtwoord-/sleutelbeheer; plaats hem nooit in Git of een chat.
8. Noteer App ID en Installation ID. Die laatste staat in de URL van de installatie-instellingen, achter `/installations/`.
9. Repository ID voor `ferrynl/ha-invest` is **1424725566** (gecontroleerd bij GitHub). Je kunt dit controleren bij `https://api.github.com/repos/ferrynl/ha-invest` (veld `id`).

De dienst maakt kortlevende installation tokens en beperkt ook die tokens expliciet tot het ingestelde repositorynummer en Issues-schrijfrechten. [GitHub-documentatie](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).

## Coolify runtime-instellingen

Voer deze waarden in onder **Environment Variables**, uitsluitend beschikbaar tijdens **runtime**, als geheim waar van toepassing. Gebruik ze niet als build arguments:

| Variabele | Inhoud |
| --- | --- |
| `SERVICE_SECRET` | Eigen willekeurig geheim van minimaal 32 tekens; stabiel bewaren en back-uppen |
| `GITHUB_WEBHOOK_SECRET` | Het afzonderlijke webhook-geheim uit de GitHub App |
| `GITHUB_APP_ID` | App ID |
| `GITHUB_INSTALLATION_ID` | Installation ID |
| `GITHUB_REPOSITORY_ID` | Repository ID van ferrynl/ha-invest |
| `GITHUB_APP_PRIVATE_KEY_B64` | De PEM-sleutel als één base64-regel, **dit blijft een geheim** |
| `TRUSTED_PROXY_CIDRS` | Alleen de daadwerkelijke bron-IP's/CIDR's van jouw Coolify-proxy; zie hieronder |

Je kunt in plaats van base64 ook een alleen-lezen Coolify File Mount gebruiken, bijvoorbeeld `/run/secrets/github-app.pem`, met `GITHUB_APP_PRIVATE_KEY_FILE=/run/secrets/github-app.pem`. Het bestand moet leesbaar zijn voor UID 10001. Verwijder dan `GITHUB_APP_PRIVATE_KEY_B64`.

Maak willekeurige geheimen in een wachtwoordmanager, via Coolify, of lokaal met `openssl rand -hex 32`. Base64 van een PEM-bestand kan op Linux met `base64 -w 0 github-app.pem`. Base64 versleutelt niets: behandel de uitvoer als de private sleutel.

**Proxy-adressen:** de dienst vertrouwt standaard geen aangeleverde IP-headers. Alleen als het directe bronadres in `TRUSTED_PROXY_CIDRS` valt, gebruikt zij `X-Real-IP` voor IP-limieten. Configureer het echte proxyadres, bij voorkeur een `/32` of `/128`, en zorg dat de proxy die header zelf overschrijft. Vertrouw nooit `0.0.0.0/0`, `::/0` of willekeurige bezoekersheaders. Bij een lege instelling telt de proxy als één IP, waardoor gedeelde limieten eerder worden bereikt. Houd toegang tot poort 8080 beperkt tot de proxy. Voeg aan de proxy een algemene verzoeklimiet en een bodylimiet van 256 KiB toe; de dienst heeft zelf ook tijd-, body-, authenticatie- en gelijktijdigheidslimieten.

Deploy. Controleer dat `https://meldingen.home-invest.nl/health` `{"ok":true}` geeft. Dat is een procescontrole, geen bewijs dat de GitHub-rechten kloppen. Controleer ook onderstaande status en één bewust aangemaakte proefmelding. De code/tests maken geen issues op jouw echte repository.

## Een installatie activeren

Open de Terminal van de centrale container in Coolify:

```sh
python -m feedback_service invite
```

Dit toont één eenmalige code, standaard 24 uur geldig. Deel hem alleen met de beheerder van de bedoelde Home Invest-installatie, via een vertrouwd kanaal. De dienst bewaart alleen een HMAC van de code. Een herhaalde aanvraag na een verloren antwoord werkt uitsluitend met dezelfde lokaal gegenereerde installatiecredential; de code kan geen tweede installatie aanmaken.

Op die Home Assistant-installatie:

1. Stel bij de Home Invest-appconfiguratie `feedback_service_url: https://meldingen.home-invest.nl` in en herstart de app.
2. Open **Wensen & bugs → Meldservice activeren** als beheerder.
3. Vul de code in. Daarna kunnen aangemelde Home Invest-gebruikers meldingen indienen, zonder GitHub-account.

De gebruiker bevestigt expliciet dat de tekst openbaar wordt. Alleen titel, beschrijving, type en appversie worden verstuurd. De centrale dienst ontvangt technisch ook het verbindings-IP; er worden alleen geheime, gehashte IP-identificaties voor tijdelijke limieten opgeslagen. Er gaan geen portefeuilledata, Home Invest-gebruikersnamen, e-mailadressen of logs mee.

Elke installatie genereert zelf een eigen willekeurige credential. Alleen de hash staat centraal; lokaal is de credential versleuteld, buiten het portefeuilledatabestand. Een portefeuille-import kan de verbinding of wachtrij niet vervangen. Gebruik een volledige Home Assistant-appback-up om die mee te herstellen.

**Activering is bewust gesloten.** Dit is geen onbeveiligde publieke zelfregistratie: duizenden installaties kunnen elk een eigen code ontvangen, maar een geautomatiseerd uitgifteportaal met eigen identiteits-/misbruikcontrole is nog niet onderdeel van deze versie. Plaats nooit een algemene activeringscode op de website of in de app.

## Limieten en aflevering

- Per installatie: 5 nieuwe meldingen per voortschrijdend venster van 24 uur; 120 geauthenticeerde API-aanvragen per uur.
- Centraal: maximaal 200 nieuwe meldingen per 24 uur, 100 nieuwe installaties per uur en 1000 nog niet afgehandelde wachtrij-items.
- Per IP: maximaal 30 activeringspogingen en 6000 algemene aanvragen per uur. Ook mislukte activeringspogingen tellen mee.
- Maximaal 32 gelijktijdige verbindingen; bodylimieten 2 KiB voor activering, 24 KiB voor een melding en 256 KiB voor een webhook.
- De lokale app verstuurt op de achtergrond iedere 45–75 seconden maximaal één aanvraag; bord en eigen statussen worden ongeveer iedere tien minuten opgehaald. Er is geen browseropslag van meldingen of credentials.
- Centraal verwerkt één worker GitHub-verzoeken achter elkaar, minimaal twee seconden tussen de taken. GitHub-limieten en Retry-After worden gerespecteerd; bordaanvragen gebruiken ETags.

Deze conservatieve startlimieten zijn bewust begrensd. Duizenden geregistreerde installaties betekenen niet duizenden gelijktijdige inzendingen. Voer vóór brede uitrol een belastingstest op jouw VPS uit, bewaak piekgebruik en stem proxy-/IP-limieten af op gedeelde verbindingen. Er is nog geen benchmark die een specifieke capaciteit op jouw VPS garandeert.

Een melding krijgt lokaal een blijvende aanvraag-ID en wordt centraal slechts één keer als wachtrij-item opgeslagen. Herhaalde verzending na een verloren netwerkantwoord levert hetzelfde item op. Identieke lokale inhoud van dezelfde melder binnen 24 uur wordt eveneens herkend.

GitHub biedt geen idempotency-sleutel voor issue-aanmaak. Als een GitHub-POST een timeout, onverwacht antwoord of 5xx geeft, of de container tijdens zo'n POST herstart, wordt de melding **uncertain**. De dienst verstuurt deze **niet automatisch nogmaals**. Een expliciete HTTP 429 mag na de wachttijd wel opnieuw geprobeerd worden. De gebruiker ziet **Controle door beheerder nodig**.

## Beheer en herstel

```sh
python -m feedback_service status
python -m feedback_service installations
python -m feedback_service owner ISSUE_NUMMER
python -m feedback_service revoke INSTALLATIE_ID
```

`status` geeft aantallen, de oudste wachtrij-tijd en ID's van onzekere meldingen, zonder beschrijvingen, credentials of IP's. `installations` toont installatie-ID's voor beheer, met paginering via `--offset` en `--limit` (maximaal 1000). `owner` zoekt de installatie achter een issue op, zodat je bij misbruik gericht kunt intrekken. Intrekken blokkeert authenticatie direct en wist nog niet verzonden centrale payloads voor die installatie. Een GitHub-aanvraag die al onderweg was kan nog worden afgerond.

Bij een onzekere aflevering zoek je op GitHub naar het item met de marker `<!-- home-invest:MELDING_ID -->` in de bron van de beschrijving. Koppel een gevonden issue zonder opnieuw aan te maken:

```sh
python -m feedback_service reconcile MELDING_ID ISSUE_NUMMER
```

De dienst controleert de marker op de vaste repository. Is er geen issue en wil je het item beëindigen, gebruik dan `python -m feedback_service discard MELDING_ID`. Er is bewust geen blinde herverzendknop voor onzekere POST's.

Bewaar een consistente SQLite-back-up van `/data/relay.sqlite3` en bewaar runtime-geheimen afzonderlijk. Gebruik SQLite's backup-API of stop de container bij het kopiëren van de database/WAL; een los bestand kopiëren tijdens schrijven is geen consistente back-up. Test herstel op een afgeschermde testinstantie **zonder actieve GitHub-worker**. Een herstel naar een oudere back-up kan al verzonden items als queued terugbrengen: vergelijk die eerst met GitHub voordat de worker opnieuw wordt gestart. Voorkom dat productie en een herstelde kopie tegelijk verzenden.

Na succesvolle publicatie worden beschrijving en appversie uit de centrale wachtrij gewist; titel, type, installatiekoppeling, inhoudshash, aanvraag-ID en issue-status blijven voor deduplicatie en opvolging bewaard. Op GitHub blijven de gepubliceerde gegevens openbaar staan. Niet verzonden centrale payloads vervallen na 30 dagen; tijdelijke IP-limieten na ongeveer een uur en webhook-afleverings-ID's na zeven dagen. Lokaal blijft een begrensde, versleutelde geschiedenis bewaard. Stel aanvullend je privacyverklaring, back-upbeleid en toegangsbeheer voor Coolify vast vóór publieke uitrol.

Bewaking: controleer naast health ook de omvang/leeftijd van de wachtrij, onzekere meldingen, GitHub-bereikbaarheid, vrije schijfruimte en back-ups. Containerlogs bevatten geen verzoekinhoud, headers, credentials of volledige tracebacks; zet proxylogging van Authorization-headers en bodies eveneens uit.

## Lokaal of zonder Coolify

```sh
docker build -f feedback_service/Dockerfile -t home-invest-feedback:0.39.0 .
```

Er staat ook een `feedback_service/compose.yaml` voor een enkele VPS met een eigen HTTPS-proxy. Kopieer `.env.example` naar `.env`, vul runtime-geheimen in en gebruik `docker compose -f feedback_service/compose.yaml up -d --build`. Die Compose publiceert alleen op `127.0.0.1:8080`. In Coolify heeft de Git/Dockerfile-route hierboven de voorkeur.
