# Aandelen Dashboard voor Home Assistant

Experimentele versie (0.2.0). Draait volledig als Home Assistant-app
(voorheen add-on), met een dashboard via de Home Assistant-zijbalk en eigen
SQLite-database. Geen externe hosting, CDN of browserbibliotheken nodig.

## Installatie via GitHub

1. De app-repository is [ferrynl/ha-invest](https://github.com/ferrynl/ha-invest).
2. De repository bevat `repository.yaml` direct in de root, met `portfolio/` ernaast.
3. Open in Home Assistant **Instellingen → Apps → App store → ⋮ → Repositories**
   (oudere versies noemen dit Add-ons).
4. Voeg `https://github.com/ferrynl/ha-invest` toe.
5. Zoek **Aandelen Dashboard**, installeer en start de app. Het bouwen kan even duren.
6. Schakel **Weergeven in zijbalk** in en open het dashboard.

Home Assistant OS met Supervisor is de beoogde installatie. Een gewone HA Container
heeft geen app store. De app is nog niet op een echte Supervisor-installatie getest.
De app bouwt uit de bron op het apparaat; er is geen containerregister nodig.

## Gebruik

De app heeft een linkerzijbalk zoals Home Assistant, met vijf afzonderlijke pagina's:

- **Home**: portefeuilletotalen en de grafiek met alle aandelen.
- **Aandelen**: posities, een aankoop toevoegen en het aankoopregister.
- **Dividend**: ontvangen dividend boeken en het dividendregister bekijken.
- **Rapporten**: ontvangen dividend per maand met jaarfilter en de actuele stand per valuta.
- **Instellingen**: standaard grafiekperiode, versiegegevens en back-ups.

Op een klein scherm opent het menu via de menuknop. De pagina staat in het
URL-fragment, zodat herladen en de terugknop blijven werken binnen HA ingress.
De standaard grafiekperiode wordt in SQLite opgeslagen en blijft na herstart behouden.

Typ minimaal twee tekens in **Zoek een aandeel**, op bedrijfsnaam of symbool.
Kies een resultaat: naam, symbool, beurs en valuta worden automatisch ingevuld.
Vul daarna alleen aantal, aankoopprijs per aandeel en aankoopdatum in.
De lijst toont de passende aandelen die Yahoo teruggeeft (maximaal 50 aangevraagd),
gefilterd op Amsterdam, Nasdaq en NYSE. Dit is geen volledige beurscatalogus;
typ meer letters om je zoekopdracht te verfijnen. Verschillende beursnoteringen
worden afzonderlijk getoond. Zoekresultaten worden kort gecachet en kunnen bij
een storing tijdelijk ontbreken. Een aankoopprijs wordt bewust niet ingevuld met
de huidige koers: die kan afwijken van wat je hebt betaald.
Voorbeelden: `ASML.AS` / AMSTERDAM / EUR; `AAPL` / NASDAQ / USD;
`IBM` / NYSE / USD. Gebruik het symbool van de juiste beursnotering.
Elke invoer is een afzonderlijke aankoop. Meerdere aankopen worden samengevoegd
in posities met hun totale inleg. Koersen worden standaard elke 15 minuten
opgehaald; `refresh_minutes` kan in de app-configuratie worden gewijzigd (5–1440).
Herstart de app na het wijzigen van deze optie.

Yahoo werkt zonder API-sleutel. Deze koppeling gebruikt een publiek, onofficieel
chart-endpoint dat Yahoo kan wijzigen of blokkeren. Dit is polling, geen realtime
stream. De vertraging verschilt per beurs. Het dashboard toont de werkelijke
koerstijd; bij storingen blijft de oude koers met oude tijd zichtbaar.
Beurs en valuta worden gecontroleerd voordat een koers wordt opgeslagen.

EUR en USD hebben afzonderlijke totalen. Er is nog geen valutaomrekening.
Ontbrekende koersen geven een onvolledig totaal in plaats van een misleidende nul.
De grafiek haalt historische dagkoersen op vanaf de eerste aankoop en toont elke
kalenderdag tot vandaag. Weekenden en dagen zonder koers gebruiken de laatst
bekende koers; dit staat ook in de tabel **Dagwaarden bekijken**. Zonder eerdere
koers blijft de waarde onbekend. Historie wordt bij opstarten, een nieuwe aankoop
en daarna dagelijks gecontroleerd en in SQLite bewaard. Een eerder gedateerde
aankoop zorgt automatisch voor het ophalen van de extra historie.
Gebruik **1W, 1M, 3M, 6M, YTD, 1Y of Alles** om te zoomen. YTD begint op 1 januari;
er wordt nooit bezit getoond vóór de eerste aankoop. Datum- en waardeassen,
aanwijzen van een dag en een tabel maken dagelijkse veranderingen zichtbaar.
Historische koersen zijn Yahoo-dagsluitingen; vandaag kan de laatste beschikbare
koers zijn. Yahoo kan historische prijzen aanpassen voor splitsingen. De app
verwerkt aantallen bij splitsingen nog niet automatisch. Winst/verlies is exclusief
kosten. Ontvangen dividend kan apart worden geboekt, zoals hieronder beschreven.

### Alle aandelen en dividend

De grafiek opent standaard met **Alle aandelen**. Elk aandeel heeft een eigen lijn
voor totale winst als percentage van de inleg, inclusief ontvangen netto dividend.
Hierdoor kun je EUR- en USD-noteringen vergelijken zonder geldbedragen bij elkaar
op te tellen. Het percentage is sinds aankoop en wordt bij zoomen niet opnieuw op
nul gezet. Het is geen tijdgewogen rendement; extra aankopen kunnen het veranderen.
Kies **Totaal portefeuille · EUR/USD** voor de gezamenlijke marktwaarde en inleg
binnen één valuta, met een aparte lijn voor waarde plus ontvangen dividend.
Individuele aandelen blijven ook selecteerbaar. Alle bestaande zoomknoppen werken
voor iedere weergave.

Onder **Ontvangen dividend** kies je een bestaand aandeel en voer je het **totale
netto ontvangen bedrag**, betaaldatum en eventueel een notitie in. Het bedrag is
in de valuta die bij het aandeel staat, niet per aandeel. Boek alleen daadwerkelijk
ontvangen bedragen, geen aangekondigde uitkeringen. Er is geen brokerkoppeling of
automatische bevestiging van ontvangst. Er is nog geen wisselkoersconversie als
je broker in een andere valuta uitbetaalt.

Dividend heeft een eigen `dividends`-tabel in SQLite, los van aankopen en koersen.
Het dividendregister, de dividendkolom en het portefeuilletotaal tonen de ontvangen
bedragen apart. **Totale winst = marktwaarde − inleg + ontvangen netto dividend**.
Dividend telt pas vanaf de betaaldatum mee in de historie en wordt niet automatisch
herbelegd of bij het aantal aandelen opgeteld. Het maakt deel uit van alle bestaande
SQLite- en Home Assistant-back-ups. De database wordt bij de update uitgebreid;
je bestaande aankopen en koershistorie blijven behouden.

## Opslag en back-ups

Alle gebruikersgegevens blijven buiten de broncode, in de persistente app-map:

```
/data/portfolio.sqlite3           aankopen en koershistorie
/data/backups/portfolio-*.sqlite3 consistente SQLite-back-ups
/data/options.json               configuratie van Home Assistant
```

De app maakt bij opstarten en daarna dagelijks een SQLite-back-up en bewaart de
laatste 30. **Back-up downloaden** maakt en downloadt direct een consistente kopie.
Deze kopieën op hetzelfde apparaat beschermen niet tegen verlies van het apparaat.
Neem de app op in de automatische Home Assistant-back-ups en bewaar die ook elders.
Herstel bij voorkeur de volledige app via Home Assistant **Instellingen → Systeem
→ Back-ups**. Een losse SQLite-kopie kun je met bestandstoegang naar de app-container
herstellen: stop eerst de app, bewaar de huidige database apart, plaats de kopie als
`/data/portfolio.sqlite3` en start opnieuw. Er is nog geen herstelknop in het dashboard.

De download bevat de volledige privéportefeuille. Upload databases, opties en
back-ups nooit naar GitHub. `.gitignore` sluit lokale gegevens uit, maar geldt niet
voor handmatige uploads via de GitHub-website.

## Ontwikkeling

### Databaseversies en migraties

Appversie en databaseschema hebben elk een eigen versienummer. Schema **4** gebruikt
`PRAGMA user_version` als opgeslagen versie. De migratierunner in `migrations.py`
voert uitsluitend ontbrekende stappen op volgorde uit:

1. Aankopen, koersen en koersindex.
2. Historische dagkoersen en synchronisatiegegevens.
3. Ontvangen dividend.
4. Dashboardinstellingen.

Vóór het aanpassen van een bestaande database wordt een consistente kopie in
`/data/backups/migrations/before-vN-to-vM-*.sqlite3` gemaakt. Deze kopieën vallen
buiten de rotatie van de 30 gewone back-ups. De volledige upgrade draait in één
transactie; bij een fout worden schema én versienummer teruggedraaid en stopt de
app. Een database uit een nieuwere app wordt geweigerd zonder downgrade. Herhaald
starten met het actuele schema voert geen migraties opnieuw uit.

Voeg bij toekomstige schemawijzigingen een nieuwe migratie en bijbehorende tests
toe; verander oude migraties niet. De projectafspraken staan ook in `AGENTS.md`.

Python 3.13, zonder externe Python-pakketten:

```
cd portfolio/app
python server.py
```

Open `http://localhost:8099/`. Gebruik lokaal `BIND=127.0.0.1`; de ontwikkelserver
heeft geen eigen login. In Home Assistant loopt toegang via authenticated ingress;
er is geen hostpoort gepubliceerd. Stel deze server niet rechtstreeks bloot.

```
python -m unittest discover -s tests -v
```

## Structuur

- `portfolio/app/storage.py`: schema, validatie, berekeningen, back-ups.
- `portfolio/app/migrations.py`: geversioneerde, transactionele database-updates.
- `portfolio/app/provider.py`: vervangbare Yahoo-koerskoppeling.
- `portfolio/app/history.py`: dagelijkse waardes met aankopen en kalenderdagen.
- `portfolio/app/server.py`: lokale HTTP-API en geplande taken.
- `portfolio/app/static/`: afzonderlijke HTML-, CSS- en JavaScript-bestanden.
- `portfolio/app/static/pages.js`: paginanavigatie, rapporten en dashboardinstellingen.
- `portfolio/config.yaml` en `Dockerfile`: HA-installatie en container.
- `tests/`: opslag- en providercontroles, zonder echte privégegevens.
- `.github/workflows/check.yml`: controles bij GitHub-wijzigingen.

## Grenzen van deze eerste versie

Alleen aankopen en handmatig geboekt netto dividend; nog geen verkopen, splitsingen, bewerkingsinterface,
transactiekosten of automatische valutawissel.
Geen HACS-integratie: installatie gaat via een HA app-repository.
Voor publieke distributie moet de geschiktheid van de koersdienst voor die toepassing
nog worden vastgesteld. Iedere installatie haalt zelf koersen op; er is geen
centrale verzameling van portefeuilles of doorlevering van koersen.

## Bronnen

- [Home Assistant app-configuratie](https://contributors.home-assistant.io/apps/reference/configuration/)
- [Home Assistant ingress](https://developers.home-assistant.io/docs/apps/presentation/)
- [Yahoo beursdekking en vertraging](https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html)
