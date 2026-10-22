# Home Invest — Uitgebreide handleiding

Experimentele versie (0.13.0). Draait volledig als Home Assistant-app
(voorheen add-on), met een dashboard via de Home Assistant-zijbalk en eigen
SQLite-database. Geen externe hosting, CDN of browserbibliotheken nodig.

## Installatie via GitHub

1. De app-repository is [ferrynl/ha-invest](https://github.com/ferrynl/ha-invest).
2. De repository bevat `repository.yaml` direct in de root, met `portfolio/` ernaast.
3. Open in Home Assistant **Instellingen → Apps → App store → ⋮ → Repositories**
   (oudere versies noemen dit Add-ons).
4. Voeg `https://github.com/ferrynl/ha-invest` toe.
5. Zoek **Home Invest**, installeer en start de app. Het bouwen kan even duren.
6. Schakel **Weergeven in zijbalk** in en open het dashboard.

Home Assistant OS met Supervisor is de beoogde installatie. Een gewone HA Container
heeft geen app store. De app is nog niet op een echte Supervisor-installatie getest.
De app bouwt uit de bron op het apparaat; er is geen containerregister nodig.

## Gebruik

De app heeft een linkerzijbalk zoals Home Assistant, met acht afzonderlijke pagina's:

- **Home**: portefeuilletotalen en de grafiek met alle aandelen.
- **Aandelen**: posities, een aankoop toevoegen en het aankoopregister.
- **Dividend**: ontvangen dividend boeken en het dividendregister bekijken.
- **Valuta**: alle beschikbare valuta, historische omrekening, opgeslagen dagkoersen en importomrekeningen.
- **Rapporten**: ontvangen dividend per maand met jaarfilter en de actuele stand per valuta.
- **Logs** (ingelogde admin): foutdetails, Log-ID zoeken, niveau-/bronfilters en JSON-download.
- **Imports** (admin): Trading 212 CSV/API controleren, beursnoteringen automatisch koppelen en importeren.
- **Instellingen** (admin): gebruikersbeveiliging, brokeraccounts, versiecontrole, standaard grafiekperiode,
  versiegegevens, back-up downloaden en terugzetten.

Op een klein scherm opent het menu via de menuknop. De pagina staat in het
URL-fragment, zodat herladen en de terugknop blijven werken binnen HA ingress.
De standaard grafiekperiode wordt in SQLite opgeslagen en blijft na herstart behouden.

Typ minimaal twee tekens in **Zoek een aandeel**, op bedrijfsnaam of symbool.
Kies een resultaat: naam, symbool, beurs en valuta worden automatisch ingevuld.
Vul daarna alleen aantal, aankoopprijs per aandeel en aankoopdatum in.
De lijst toont de passende aandelen die Yahoo teruggeeft (maximaal 50 aangevraagd),
gefilterd op Amsterdam, Nasdaq en NYSE. Dit is geen volledige beurscatalogus;
typ meer letters om je zoekopdracht te verfijnen. Verschillende beursnoteringen
worden afzonderlijk getoond. Zoekresultaten worden een week in SQLite gecachet en kunnen bij
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
koers zijn. Yahoo kan historische prijzen aanpassen voor splitsingen. De Trading 212-import verwerkt aandelensplitsingen met behoud van de totale kostprijs. Winst/verlies is exclusief
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

### Brokeraccounts en Trading 212-import

Maak onder **Instellingen → Brokeraccounts** een rekening aan met een eigen naam
en het bedrijf, bijvoorbeeld `Trading 212`. Dit is los van je loginaccount.
Meerdere rekeningen bij hetzelfde bedrijf zijn toegestaan. Bestaande gegevens gaan
bij de update naar **Handmatig**; de app gokt niet bij welke broker je ze bezit.
Kies bovenaan een rekening of **Alle accounts**. Nieuwe handmatige aankopen en
dividend krijgen ook een brokeraccount. Koersen worden per beursnotering gedeeld,
maar aantallen, kostprijs en dividend worden per rekening berekend.

Trading 212 ondersteunt zowel **History CSV** als een **API-verbinding**. De API
haalt een officieel CSV-rapport op en gebruikt dezelfde preview, beurskoppeling en
bron-ID-controles als een handmatige upload. Hierdoor worden overlappende API- en
CSV-imports per rekening gecontroleerd op dubbele transacties.

#### Verbinden via de API

1. Schakel gebruikersbeveiliging in bij Instellingen en meld je aan als admin.
2. Maak een brokeraccount aan met bedrijf **Trading 212**. Gebruik aparte rekeningen
   voor Live en Demo; verbind nooit verschillende werkelijke rekeningen aan één brokeraccount.
3. Maak in Trading 212 een API key en secret met uitsluitend toegang tot historische
   rapporten/exports. Schakel geen handelsrechten in. Eventuele IP-beperking moet
   het uitgaande IP-adres van je HA-installatie toestaan.
4. Ga naar **Imports → Trading 212 API**, kies brokeraccount en Live/Demo en sla
   de sleutel en secret op. Opgeslagen betekent nog niet dat de API ze heeft geaccepteerd.
5. Kies de volledige relevante transactieperiode en klik **Rapport via API aanvragen**.
6. Controleer na circa een minuut **Rapportstatus controleren en ophalen**. Langere
   perioden worden in delen van maximaal 364 dagen aangevraagd (Trading 212 staat
   maximaal één jaar per rapport toe). Iedere statuscontrole haalt een gereed deel op
   en vraagt zo nodig het volgende aan. De teller toont de voortgang; de taak en
   deelrapporten overleven een app-herstart. Herhaal de statuscontrole ongeveer iedere
   minuut totdat het complete importvoorbeeld verschijnt. Je hoeft niet per deel te boeken.
7. Controleer het opgehaalde voorbeeld en de automatische koppelingen en bevestig de import.

De app gebruikt alleen de officiële rapport-endpoints; er worden geen orders geplaatst.
Statusantwoorden worden 60 seconden gecachet; het rapport en originele transacties
blijven in SQLite. Ook mislukte verzoeken worden lokaal begrensd. Een volgende import
start je zelf; er is nog geen geplande automatische brokersynchronisatie.
Downloaden van het rapport verstuurt nooit de API-credentials naar de downloadhost.
Alleen HTTPS-downloads vanaf Trading 212, CloudFront en S3 worden geaccepteerd;
redirects worden geweigerd. Bij een ander downloadadres blijft handmatige CSV beschikbaar.

API-sleutels staan versleuteld met Fernet in `/data/connections/`, met een aparte
lokale encryptiesleutel en beperkte Linux-bestandsrechten. Ze gaan niet naar de browser,
provider-cache of de downloadbare SQLite-back-up. De encryptiesleutel staat op hetzelfde
HA-apparaat: versleuteling beschermt niet tegen volledige toegang tot dat apparaat.
Neem de volledige appdata op in een Home Assistant-back-up om verbindingen mee te nemen.
Bij alleen SQLite-herstel blijven lokale verbindingen behouden als het brokeraccount
hetzelfde is; anders moet je opnieuw verbinden. **Verbinding verwijderen** verwijdert
alleen de opgeslagen toegang; geïmporteerde gegevens blijven staan. Trek voor definitieve
intrekking ook de sleutel in bij Trading 212. Deel sleutels nooit via GitHub of chat.

De [officiële API-documentatie](https://docs.trading212.com/api) beschrijft Basic-auth
met key/secret, Invest/Stocks ISA, de asynchrone rapporten en aanvraaglimieten.
Dezelfde importbeperkingen voor kosten, acties en dividendvaluta gelden voor API en CSV.

#### CSV handmatig uploaden

1. Exporteer bij Trading 212 via **History → Export** je orders en dividend.
2. Maak in Home Invest een rekening met bedrijf **Trading 212**.
3. Open **Imports**, kies rekening en CSV en klik **Voorbeeld controleren**.
4. Controleer alle regels; de app koppelt tickers automatisch aan de Yahoo-beursnotering.
   De app kiest geen onduidelijke notering of wisselkoers automatisch.
5. Bevestig het voorbeeld en klik **Import definitief opslaan**.

Ondersteund: kooporders, verkooporders en ontvangen cashdividend. Verkopen gebruiken
een voortschrijdende gemiddelde kostprijs. Resterend bezit en gerealiseerde winst
blijven per rekening gescheiden; de koerswinst bevat gerealiseerde en ongerealiseerde
winst. **Totale winst = marktwaarde − resterende kostprijs + gerealiseerde winst +
ontvangen dividend**. Bij verkopen kan de getoonde resterende inleg dalen. De
procentuele aandeellijn gebruikt de totale historische aankoopinleg als noemer.
Dit is een praktisch portefeuilleoverzicht, geen fiscale berekening.

Importeer de volledige relevante aankoopgeschiedenis. Een verkoop die groter is
dan het beschikbare bezit blokkeert de hele import. Ook onbekende acties zoals
splitsingen blokkeren de import; er worden dan geen gedeeltelijke boekingen gemaakt.
Bekende stortingen, opnames en renteregels worden zichtbaar overgeslagen omdat de
app geen bank-/cashsaldo bijhoudt. Transactiekosten, bronbelastingberekeningen,
valutawissels en CFD's worden niet verwerkt. Voor dividend moet `Currency (Total)`
overeenkomen met de noteringsvaluta. Exporteer bij een afwijkende dividendvaluta
eerst alleen de orders; omzetting van dat dividend moet je apart controleren.

Bron-ID's en inhoudscontroles voorkomen dubbele import per brokeraccount, ook bij
overlappende exports en na back-upherstel. Een gewijzigde bestaande bron-ID wordt
geweigerd. Bij ontbrekende ID's wordt een inhoudsvingerafdruk gebruikt; onduidelijke
identieke regels worden geweigerd. De originele regels en previews blijven in SQLite
bewaard. Handmatig geboekte transacties hebben geen brokerbron-ID: importeer dezelfde
werkelijke transacties niet nogmaals naast je handmatige kopie.

Nieuwe aanbieders krijgen een eigen adapter in `portfolio/app/imports/` en een
registratie in `ADAPTERS`. Preview, accountkoppeling, bevestiging, bronregistratie en
deduplicatie zitten in de gemeenschappelijke importservice. Alleen admins kunnen
brokeraccounts aanmaken of importeren; Basic kan rekeningen bekijken en de bestaande
handmatige portefeuillefuncties gebruiken.

### Duurzame API-cache en versiecontrole

Succesvolle Yahoo-antwoorden worden volledig als JSON opgeslagen in `api_cache`,
naast de afzonderlijke koersen en daghistorie. De cache overleeft herstarten en
zit in back-ups. Zoek-/instrumentresultaten worden **7 dagen** hergebruikt,
actuele koersen gedurende het ingestelde koersinterval en historieaanvragen één dag.
Historische dagwaarden blijven in `daily_prices` staan; na de eerste import worden
alleen ontbrekende/recent overlappende dagen opgehaald, niet steeds de hele historie.
Een eerder gedateerde aankoop kan wel een extra historische aanvraag vereisen.
Gelijke beursnoteringen bij verschillende brokers worden maar één keer ververst.
Foutantwoorden worden niet als succesvolle API-cache bewaard.

Onder **Instellingen → Versiecontrole** controleer je de nieuwste gepubliceerde
appconfiguratie op GitHub. Het resultaat staat één dag in SQLite, met controletijd.
De app vergelijkt versienummers numeriek. Deze knop installeert niets; bijwerken
blijft via de Home Assistant app store lopen.

### Gebruikers en rollen

Onder **Instellingen → Gebruikersbeveiliging** kun je accounts inschakelen.
Bij de eerste keer maak je zelf een adminaccount met een wachtwoord van minimaal
12 en maximaal 128 tekens. Er zijn geen standaardaccounts of standaardwachtwoorden.
Bij uitgeschakelde gebruikersbeveiliging blijft de bestaande Home Assistant-ingress
de toegang verzorgen. Schakel de optie in voordat je de portefeuille met andere
HA-gebruikers deelt.

- **Admin**: alle pagina's, invoer, instellingen, gebruikersbeheer en back-ups/herstel.
- **Basic**: Home, Aandelen, Dividend en Rapporten, inclusief aankopen en dividend
  invoeren. Geen instellingen, gebruikersbeheer, back-updownload of herstel.

Dit is één gedeelde portefeuille, niet een aparte portefeuille per gebruiker.
Rechten worden op iedere API-aanvraag op de server afgedwongen. Een rechtstreeks
API-verzoek omzeilt de rol niet. Admins kunnen accounts aanmaken, rollen wijzigen,
wachtwoorden resetten en accounts deactiveren. De laatste actieve admin kan niet
worden gedeactiveerd of tot basic worden teruggezet. Maak bij voorkeur een tweede
admin aan voor herstel bij een vergeten wachtwoord; er is geen verborgen herstelaccount.
Linksonder in het zijmenu staat de gebruikershoek met naam, rol, **Account aanpassen**
en **Uitloggen**. Als je bent uitgelogd staat daar **Inloggen**. Via Account aanpassen
wijzig je je eigen gebruikersnaam en eventueel je wachtwoord; je huidige wachtwoord
is altijd vereist. Laat het nieuwe wachtwoord leeg om het bestaande te behouden.
Gewijzigde accounts moeten
opnieuw aanmelden. Alleen een admin met het huidige adminwachtwoord kan beveiliging
uitschakelen. Bij opnieuw inschakelen zijn bestaande admingegevens vereist.

Wachtwoorden worden met een unieke salt en PBKDF2-HMAC-SHA256 (600.000 iteraties)
opgeslagen. Sessies gebruiken willekeurige tokens in HttpOnly/SameSite=Strict-cookies;
de server bewaart alleen de tokenhash. Cookies krijgen Secure bij HTTPS-toegang.
Gebruik Home Assistant via HTTPS; de app publiceert geen eigen hostpoort. Schrijfacties
hebben CSRF-controle. Een sessie verloopt na 30 minuten zonder aanvragen of uiterlijk
na 8 uur, en vervalt bij uitloggen, accountwijziging of serverherstart. Er is een
limiet van 10 mislukte pogingen per gebruikersnaam en verbindingsadres in 15 minuten.
Via ingress kan het verbindingsadres gedeeld zijn; de limiet kan dan meerdere
gebruikers raken. Sessies en pogingstellers zijn bewust alleen in het geheugen.

### Downloaden en terugzetten

De downloadknop staat alleen op **Instellingen**. Daar kan een admin ook een
SQLite-back-up van maximaal 25 MB selecteren en na bevestiging terugzetten.
De app controleert het bestandsformaat, de integriteit, schemaversie en waarden.
Alleen portefeuillegegevens en de standaard grafiekperiode worden geïmporteerd;
tabellen, triggers en uitvoerbaar schema uit het bestand worden nooit overgenomen.
Oudere ondersteunde back-ups worden in het huidige schema ingelezen.

Vóór herstel maakt de app een veiligheidskopie in `/data/backups/restores/`.
Het vervangen van de portefeuille is transactioneel: een mislukte import draait
terug. **Huidige gebruikers, wachtwoorden, rollen en de beveiligingsoptie blijven
behouden**, zodat een oude back-up de beveiliging niet kan uitschakelen. Alle
sessies vervallen na succesvol herstel. Voor volledig systeemherstel inclusief
accounts gebruik je een Home Assistant-back-up van de app.

Een gedownloade volledige SQLite-kopie bevat ook accountnamen en wachtwoordhashes.
Behandel back-ups als vertrouwelijk en bewaar ze veilig; SQLite-bestanden zijn
niet zelfstandig versleuteld.

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
`/data/portfolio.sqlite3` en start opnieuw. Bij deze volledige handmatige vervanging
worden ook de accounts uit die kopie gebruikt.

De download bevat de volledige privéportefeuille. Upload databases, opties en
back-ups nooit naar GitHub. `.gitignore` sluit lokale gegevens uit, maar geldt niet
voor handmatige uploads via de GitHub-website.

## Ontwikkeling

### Databaseversies en migraties

Appversie en databaseschema hebben elk een eigen versienummer. Schema **11** gebruikt
`PRAGMA user_version` als opgeslagen versie. De migratierunner in `migrations.py`
voert uitsluitend ontbrekende stappen op volgorde uit:

1. Aankopen, koersen en koersindex.
2. Historische dagkoersen en synchronisatiegegevens.
3. Ontvangen dividend.
4. Dashboardinstellingen.
5. Gebruikers, rollen en de optie voor gebruikersbeveiliging.
6. Brokeraccounts, aankoop/verkooptype, importbatches, bronregels en blijvende API-cache.
7. Afgeschermde diagnostische logs.
8. Valuta, dagreferentiekoersen en importomrekeningen.
9. Blijvende aandelenkoppelingen.
10. Te beoordelen importregels en afzonderlijke kapitaalterugbetalingen.
11. Splitsingsmetadata met behoud van kostprijs, inleg en gerealiseerde winst.

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

Open `http://localhost:8099/`. Gebruik lokaal `BIND=127.0.0.1` en schakel accounts
in als je de ontwikkelserver met anderen deelt. In Home Assistant loopt toegang via authenticated ingress;
er is geen hostpoort gepubliceerd. Stel deze server niet rechtstreeks bloot.

```
python -m unittest discover -s tests -v
```

## Structuur

- `portfolio/app/storage.py`: schema, validatie, berekeningen, back-ups.
- `portfolio/app/migrations.py`: geversioneerde, transactionele database-updates.
- `portfolio/app/security.py`: wachtwoorden, sessies en accountbeheer.
- `portfolio/app/web.py`: API, authenticatie, rollen en CSRF-controles.
- `portfolio/app/restore.py`: gevalideerd, transactioneel portefeuilleherstel.
- `portfolio/app/cache.py`: tijdelijke cache van het portefeuilleoverzicht.
- `portfolio/app/persistent_cache.py`: blijvende cache voor providerantwoorden.
- `portfolio/app/imports/`: uitbreidbare brokeradapters en importservice.
- `portfolio/app/updates.py`: gecachete, alleen-lezen GitHub-versiecontrole.
- `portfolio/app/provider.py`: vervangbare Yahoo-koerskoppeling.
- `portfolio/app/history.py`: dagelijkse waardes met aankopen en kalenderdagen.
- `portfolio/app/server.py`: lokale HTTP-API en geplande taken.
- `portfolio/app/static/`: afzonderlijke HTML-, CSS- en JavaScript-bestanden.
- `portfolio/app/static/pages.js`: paginanavigatie, rapporten en dashboardinstellingen.
- `portfolio/config.yaml` en `Dockerfile`: HA-installatie en container.
- `tests/`: opslag- en providercontroles, zonder echte privégegevens.
- `.github/workflows/check.yml`: controles bij GitHub-wijzigingen.

## Grenzen van deze eerste versie

### Caching

Het berekende portefeuilleoverzicht wordt 30 seconden in het servergeheugen bewaard.
Elke wijziging, koersupdate en herstelactie maakt die cache ongeldig. De browser
gebruikt ETags om identieke overzichten niet opnieuw te downloaden. Financiële en
accountantwoorden krijgen `no-store`; er staat geen portefeuillecache in localStorage.
Het scherm controleert maximaal elke twee minuten zolang het tabblad zichtbaar is.
Terugkeren naar het tabblad controleert de lokale stand opnieuw. Dat start geen
Yahoo-koersaanvraag.

Yahoo-koersen worden alleen via de achtergrondtaak gecontroleerd. Een recent in
SQLite opgeslagen koers wordt gedurende het ingestelde interval hergebruikt, ook
na een nieuwe aankoop van hetzelfde aandeel. Dagkoersen blijven dagelijks gecachet;
zoeken gebruikt een korte cache en een typevertraging. Statische bestanden gebruiken
een appversie in de URL, ETags en maximaal één dag browsercache. Een app-update
verandert de asset-URL's automatisch.

Aankopen, geïmporteerde verkopen en netto dividend; nog geen splitsingen, bewerkingsinterface,
transactiekosten of automatische valutawissel.
Geen HACS-integratie: installatie gaat via een HA app-repository.
Voor publieke distributie moet de geschiktheid van de koersdienst voor die toepassing
nog worden vastgesteld. Iedere installatie haalt zelf koersen op; er is geen
centrale verzameling van portefeuilles of doorlevering van koersen.

## Bronnen

- [Home Assistant app-configuratie](https://contributors.home-assistant.io/apps/reference/configuration/)
- [Home Assistant ingress](https://developers.home-assistant.io/docs/apps/presentation/)
- [Yahoo beursdekking en vertraging](https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html)
- [Trading 212 publieke API](https://docs.trading212.com/api)
- [Trading 212 CSV exporteren](https://helpcentre.trading212.com/hc/en-us/articles/360016898917-Can-I-export-the-trading-data-from-my-account)


## Importwijzigingen en versiegeschiedenis

Trading 212 herkent kapitaalterugbetalingen automatisch en bewaart ze apart onder
**Imports → Te beoordelen**, zonder ze als dividendwinst te tellen.
**Stock split open** stelt het nieuwe totale aantal in; de totale kostprijs,
inleg en gerealiseerde winst blijven behouden. Een bijbehorende **Stock split close**
controleert het oude aantal. Importeer de volledige aankoopgeschiedenis vóór de splitsing.
Ongeldige aantallen en ontbrekend bezit blijven ter beoordeling staan.

Probeer eerder afgewezen regels opnieuw via **Imports → Te beoordelen → Opnieuw proberen**.
Eerdere handmatige keuzes en geboekte transacties blijven behouden.
Het databaseschema is **11**. Zie [CHANGELOG.md](../CHANGELOG.md) voor de versiegeschiedenis
en [README.md](../README.md) voor aanvullende documentatie.


### Aandelensplitsingen en kapitaalterugbetalingen

Een split open stelt het volledige nieuwe aantal aandelen in; het is geen extra aankoop.
Een close op hetzelfde tijdstip controleert het oude aantal. Een losse close, meerdere
open/close-regels voor hetzelfde instrument/tijdstip, ontbrekend bezit of een afwijkend
oud aantal blijft ter beoordeling. De app schat geen kostprijs en maakt geen bezit uit niets.
De koerskolom in het transactieregister toont bij splitsingen geen aankoopprijs.

Kapitaalterugbetalingen vereisen geen beurskoppeling of historische omrekening en blijven
in de oorspronkelijke valuta. De ontvangst staat onder Imports → Te beoordelen in het
afzonderlijke overzicht, ook als er geen openstaande beoordelingen zijn. Er wordt geen
automatische fiscale kostprijscorrectie gedaan.

Schema 11 voegt purchases.split_before toe. Oudere back-ups krijgen bij herstel lege
splitsingsmetadata; nieuwe back-ups behouden splitsingen en de bestaande administratie.


## Transacties bekijken en wijzigen (0.12.0)

Open **Transacties** in het zijmenu. De rekeningkeuze bovenaan geldt voor deze lijst;
zoek op aandeel, broker of datum en filter op transactietype. De lijst toont 50 regels
per pagina. **Bekijken** opent de gegevens en de volledige wijzigingshistorie.
Basic-gebruikers kunnen bekijken; alleen admins kunnen wijzigingen opslaan.

Bij aankopen en verkopen kun je datum, tijd, aantal, prijs en aankoop/verkooptype wijzigen.
Bij dividend kun je datum, netto bedrag en notitie wijzigen. Bij kapitaalterugbetalingen
zijn datum en bedrag aanpasbaar; ze blijven buiten dividendwinst.
Bij splitsingen kun je datum, tijd en het nieuwe aantal aanpassen. Het oude aantal
uit de bron blijft als controle behouden. Brokeraccount, aandeel en valuta blijven vaststaan.
Een wijziging die latere verkopen of splitsingen ongeldig maakt, wordt volledig teruggedraaid.

De oorspronkelijke importregel, gebruikte bron-ID en oorspronkelijke valutaomrekening
blijven als bronadministratie bewaard. Een correctie past de geboekte ledger aan;
de wijzigingshistorie vermeldt vóór/na, tijd en gebruiker. Opnieuw importeren van dezelfde
bronregel maakt de handmatige correctie niet ongedaan. Vernieuw het overzicht als een
andere sessie de transactie intussen heeft gewijzigd.

## Portefeuillegegevens verwijderen

Open **Instellingen → Portefeuillegegevens verwijderen**. Kies **Alles** of één
brokeraccount en bekijk het verwijderoverzicht. Typ **VERWIJDEREN** en kies
**Getoonde gegevens verwijderen**. Een intussen gewijzigde administratie vereist een
nieuw overzicht. Zonder succesvolle veiligheidsback-up wordt niets verwijderd.

Verwijderd worden de gekozen aankopen, verkopen, splitsingen, dividend, kapitaalterugbetalingen,
imports, bron-ID-registraties, importomrekeningen, beoordelingen, aandelenkoppelingen
en wijzigingshistorie. Bij Alles worden ook gedeelde aandelenkoersen, synchronisatiestatus
en API-cache gewist. Bij één brokeraccount blijven gedeelde koersen en andere rekeningen behouden.
Brokeraccounts zelf, gebruikers, wachtwoorden, beveiliging, appinstellingen, referentiekoersen
voor valuta en opgeslagen API-verbindingen blijven behouden. Lopende API-rapportaanvragen
blijven eveneens beschikbaar; ophalen maakt een nieuw importvoorbeeld.

Een volledige back-up van de portefeuille vóór verwijderen staat in
/data/backups/deletions/before-delete-portfolio-*.sqlite3, buiten de gewone rotatie.
Download deze via de link die na verwijderen verschijnt (alleen admin). Terugzetten
via de bestaande back-upfunctie herstelt de volledige portefeuille, inclusief andere rekeningen
zoals ze op het moment van de back-up waren. De bron-ID’s van gewiste imports worden
eveneens gewist, zodat je die gegevens bewust opnieuw kunt importeren.

Schema **12** voegt transaction_edits toe; de bestaande schema-11-splitsingsmetadata
blijft ongewijzigd. Back-upherstel ondersteunt wijzigingshistorie en oudere back-ups.


## Home en bewerkpop-ups (0.13.0)

Home begint direct bij het portefeuilleoverzicht. De algemene kop met MIJN PORTEFEUILLE,
Home, de brokerselector en de koersstatusbalk zijn op deze pagina verborgen.
Op andere pagina’s blijven de rekeningkeuze en status beschikbaar. De mobiele
menuknop werkt ook op Home.

Bewerken gebeurt altijd in een modale pop-up: transacties, aandelenkoppelingen,
importclassificatie, gebruikers en instellingen. Toevoegen van aankopen, dividend
en brokeraccounts, API-verbindingen, beveiliging, herstellen en verwijderen gebruiken
dezelfde pop-upstijl. Lees- en zoekfilters blijven rechtstreeks op de pagina staan.

Open het formulier via de bijbehorende knop. Sla expliciet op om de wijziging door
te voeren. Sluiten, Annuleren of Escape slaat niets op. De achtergrond is tijdens
bewerken niet bedienbaar en de toetsenbordfocus blijft in de pop-up. Bij navigatie
en afmelden sluiten geopende pop-ups; wachtwoordvelden worden geleegd.
Databaseschema en bestaande transacties blijven ongewijzigd.

### Kolomfilters en importdiagnostiek (0.14.0)
Elke tabel heeft onder de kolomkoppen zoekvelden. Meerdere velden worden gecombineerd; leegmaken heft een filter op. Home filtert alle posities binnen de gekozen valuta en algemene filters vóór paginering. Tabellen met een laadlimiet (zoals logs en dagwaarden) filteren de geladen regels; laad zo nodig extra regels. Filters worden alleen in het geheugen van de pagina bewaard.

Aantallen zoals `0E-8` zijn exact nul en worden als `0` getoond. Fractionele aandelen behouden hun decimalen. API-import gebruikt het historische exportbestand, geen live bezitcontrole. Controleer bij afwijkingen de gekozen periode, aandelenkoppelingen en Te beoordelen. Diagnostische logs tonen per import het batchnummer, account, regelaantallen en afgewezen regels. Bij te grote verkopen of afwijkende splitsingen staan de betrokken aantallen in de details; bronbestanden en sleutels worden niet gelogd.

### Aandeeldetails en categorieën (0.15.0)
Klik in Aandelen op de naam van een positie. De detailpagina toont de opgeslagen prijs per aandeel, met periodekeuze, en de gebeurtenissen voor het gekozen brokeraccount (of alle accounts). Slotkoersen en de laatste koersmeting worden onderscheiden. Er wordt bij het openen geen provider opgevraagd; ontbrekende historie wordt aangevuld door de bestaande automatische koerscontrole.

Sector, land, type belegging en eigen categorie gelden per combinatie van ticker, beurs en valuta. Admins vullen ze in via Categorieën aanpassen. Ontbrekende indelingen blijven Niet ingedeeld; er wordt geen sector of vestigingsland afgeleid uit de beurs. De indeling staat in de aandelenlijst en in de opgeslagen gegevens voor latere rapportages, en wordt meegenomen in back-upherstel. Kapitaalterugbetalingen en openstaande importregels worden alleen getoond bij een eenduidige aandelenkoppeling; onbekende bronregels blijven bij Imports beschikbaar.

Elke kolomkop is een sorteerknop: opnieuw klikken keert de volgorde om. Getallen en datums worden passend gesorteerd, onbekende waarden staan onderaan. Op Home en Transacties werken kolomfilters en sortering over alle pagina’s binnen de gekozen selectie. Andere tabellen sorteren de geladen regels. Een volledige portefeuilleverwijdering wist ook de gedeelde categorieën; verwijderen van één brokeraccount behoudt ze voor de overige accounts.

### Automatische categorieën (0.16.0)
Bij de automatische koerscontrole haalt de app per beursnotering één keer sector, vestigingsland en type belegging uit de Yahoo-profiel-API. Dit geldt ook voor al aanwezige aandelen en gesloten posities. De app controleert ticker, beurs en valuta. Als de anonieme profiel-API niet toegankelijk is, wordt dezelfde ingesloten API-respons op Yahoo’s publieke profielpagina gelezen. Alleen de geselecteerde categorievelden worden gecachet; anonieme sessiecookies en autorisatiegegevens blijven buiten database, back-ups en logs.

Een succesvol profiel blijft opgeslagen en wordt na een herstart of paginabezoek niet opnieuw opgehaald. Ontbrekende bronvelden blijven leeg; bij ETF’s is bijvoorbeeld niet altijd een sector of vestigingsland beschikbaar. Er wordt niets afgeleid uit de beurs of beursvaluta. De detailpagina toont de API-status en ophaaldatum. Mislukte aanvragen krijgen een wachttijd van minimaal 15 minuten, oplopend tot een dag, met respect voor provider-wachttijden en een veilige diagnostische melding.

Handmatige wijzigingen beschermen alleen het gewijzigde veld, ook als je een automatisch ingevuld veld bewust leegmaakt. De eigen categorie blijft altijd je eigen keuze. Niet-lege categorievelden uit eerdere versies worden bij migratie en oud back-upherstel als handmatig beschermd. Automatische voortgang en handmatige bescherming worden in nieuwe back-ups bewaard.

### Profielaanvragen en HTTP 406 (0.16.1)
Profielpagina’s worden als HTML aangevraagd, de anonieme sessiecode als tekst en de directe profiel-API als JSON. Bij HTTP 406 op de directe route probeert de app de ingesloten API-respons op de profielpagina. Blijft ook die aanvraag mislukken, dan tonen de diagnostische logs de precieze stap (`cookie_bootstrap`, `session_crumb`, `quote_summary` of `profile_page`), host, verwacht formaat en HTTP-status. Cookies, sessiecodes en antwoordinhoud worden niet gelogd. Een ETF kan een geldig gedeeltelijk profiel hebben: ontbrekend sector- of landinformatie wordt niet geschat.

### Voortgang bij grote portefeuilles (0.16.2)
De aandelenpagina haalt tijdens het aanvullen iedere vijf seconden alleen de actuele lokaal opgeslagen categorieën en voortgang op. Deze aanvraag gebruikt geen externe API en bouwt geen portefeuillehistorie opnieuw op. Gereed gemelde aandelen verschijnen direct, zonder op het einde van de volledige koersronde of de normale schermverversing te wachten. Als de ronde klaar is, wordt minder vaak gecontroleerd. Weergave vernieuwen controleert uitsluitend de lokale gegevens.

Nog ophalen en Wordt opgehaald geven lopend werk aan. Ophalen mislukt duidt op een aanvraag met wachttijd. Niet beschikbaar bij bron betekent dat het profiel succesvol is opgehaald maar de bron dat veld niet levert; dit komt onder meer bij ETF’s voor. Handmatig leeg is een bewust beschermde correctie. Eigen categorie blijft Zelf te kiezen totdat je deze zelf instelt. De voortgang telt unieke beursnoteringen binnen het gekozen brokeraccount; dezelfde notering op meerdere accounts wordt één keer opgehaald.
