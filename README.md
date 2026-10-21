# Home Invest voor Home Assistant

Experimentele versie (0.10.0). Draait volledig als Home Assistant-app
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

Appversie en databaseschema hebben elk een eigen versienummer. Schema **6** gebruikt
`PRAGMA user_version` als opgeslagen versie. De migratierunner in `migrations.py`
voert uitsluitend ontbrekende stappen op volgorde uit:

1. Aankopen, koersen en koersindex.
2. Historische dagkoersen en synchronisatiegegevens.
3. Ontvangen dividend.
4. Dashboardinstellingen.
5. Gebruikers, rollen en de optie voor gebruikersbeveiliging.
6. Brokeraccounts, aankoop/verkooptype, importbatches, bronregels en blijvende API-cache.

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

### Diagnostische logs (0.5.1)

Open **Logs** in het zijmenu als ingelogde admin. Gebruikersbeveiliging moet
hiervoor ingeschakeld zijn. Basic-gebruikers, uitgelogde bezoekers en toegang zonder
gebruikersbeveiliging krijgen ook via de API geen logs.

Trading 212-fouten tonen nu de HTTP-status en een Log-ID. Voer een mislukte aanvraag
na de update opnieuw uit: de eerdere algemene foutmeldingen zijn niet achteraf
te reconstrueren. Zoek de Log-ID, kies eventueel **Fouten** en **trading212**, en
open **details**. Daar staan methode, endpoint, Live/Demo, rapportperiode,
HTTP-status, providerfoutcode/-melding, request-ID, Retry-After en duur voor zover
beschikbaar. Netwerkfouten tonen de foutsoort en afgeschermde netwerkreden.
Geen volledige responsebody, CSV-inhoud, aanvraagheaders of traceback wordt opgeslagen.

De gedeelde module `diagnostics.py` bewaart maximaal 5.000 regels en 7 dagen
in SQLite. Zij logt ook fouten bij marktdata, achtergrondtaken en afgewezen
app-aanvragen. Nieuwe modules gebruiken `record`, `operation` of `current_record`;
voer nooit onbewerkte credentials of volledige financiële payloads als details in.
Bekende credentials, geheime velden, autorisatie, e-mailadressen en URL's worden
centraal afgeschermd. De pagina gebruikt uitsluitend tekstweergave voor logdetails.

Logs verversen op aanvraag en tonen 100 regels per pagina. Filter op niveau en bron,
zoek een Log-ID of melding, blader naar oudere regels of download de getoonde
pagina als JSON. Er wordt niets in browseropslag bewaard. Logs horen bij de lokale
installatie: een SQLite-back-up bevat ze, maar portefeuilleherstel importeert geen
oude logregels en behoudt de huidige logs. Schema 7 voegt de logtabel toe met de
bestaande migratie- en veiligheidsback-upprocedure.

### Meerjarige Trading 212-rapporten (0.5.2)

De fout `Time range requested cannot exceed 1 year` wordt voorkomen door de
rapportperiode op te splitsen. Deelrapporten overlappen op hun tijdgrens om gaten
te voorkomen; bestaande bron-ID-controle voorkomt dubbele boekingen. De volledige
preview wordt pas aangemaakt als alle delen zijn opgehaald. Lege jaren worden
meegenomen zonder boekingen; een volledig lege periode meldt dat er geen transacties zijn.
Bij een fout blijven opgehaalde delen behouden; gebruik opnieuw de statusknop om
verder te gaan. **Lokale rapportaanvraag wissen** verwijdert de wachtrij, niet eerder
geïmporteerde transacties of de API-verbinding. De bestaande grens van 5 MB en 10.000
regels geldt voor het gecombineerde rapport; kies bij overschrijding kortere perioden.
De begindatum staat standaard op 1 januari van het huidige jaar. Kies voor de eerste
import zelf de datum van je eerste transactie, zodat ook de kostprijs volledig is.
Bestaande API-verbindingen, lopende oude rapporten en schema 7 blijven behouden.

### Concrete lokale foutredenen (0.5.3)

Lokale Trading 212-controles tonen nu hun concrete melding in de logkolom en
`reason`/`code` in details, bijvoorbeeld `request_already_pending`, `request_missing`,
`poll_cooldown`, `download_host_rejected` of `csv_columns_missing`. Waar bekend staan
ook de importstap, omgeving, rapportnummer, opgehaalde/totale delen, actieve periode
en resterende wachttijd erbij. Een geweigerd downloadadres toont alleen het domein,
nooit het volledige of ondertekende adres.

Alleen expliciet veilige, door de app geschreven `ActionError`-meldingen worden
als reden gelogd. Tekst van onbekende externe exceptions en aanroepargumenten blijft
weggelaten. Een bestaande log met alleen `ValueError` kan niet achteraf worden
hersteld: voer de actie na bijwerken opnieuw uit. Schema blijft 7; verbindingen en
lopende importplannen blijven behouden.

### Trading 212 datumkolommen (0.5.4)

Zowel `Time` als `Time (UTC)` wordt ondersteund voor handmatige CSV en API-rapporten.
API-deelrapporten mogen verschillende datumkolomnamen en aanvullende belastingkolommen
hebben; originele veldwaarden blijven behouden. Als beide datumkolommen op één regel
gevuld zijn en verschillende tijden bevatten, wordt de regel geblokkeerd.
Bestaande bron-ID's blijven behouden; hetzelfde record met een andere datumkolomnaam
wordt bij de gebruikelijke tijdnotatie niet opnieuw geboekt.

Na de fout `csv_columns_missing` met een aanwezige kolom `Time (UTC)` hoef je geen
nieuw rapport aan te vragen: werk bij en klik **Rapportstatus controleren en ophalen**.
Reeds opgeslagen deelrapporten worden lokaal opnieuw verwerkt, ook als alle delen al
waren opgehaald. Wis de lopende aanvraag hiervoor niet. Schema blijft 7.

### Automatische beurskoppeling (0.6.0)

Importvoorbeelden zoeken en controleren beursnoteringen automatisch. Er is geen
zoekknop of keuzelijst per aandeel meer: controleer het overzicht en bevestig de
import één keer. ISIN (indien aanwezig), broker-ticker, bronvaluta en actuele
koersmetadata bepalen de koppeling. Broker-suffixen zoals `_US_EQ` worden herkend.
De zoekdienst ondersteunt nu ook ETF's en onder meer NYSE Arca/AMEX, Xetra, Parijs
en Milaan naast Amsterdam, Nasdaq en NYSE.

Geslaagde koppelingen staan op de previewregels en in de SQLite-cache (7 dagen);
bewezen eerdere importkoppelingen worden hergebruikt. Geen passende notering,
meerdere mogelijke noteringen, een koersdienststoring of een afwijkende valuta
blijft zichtbaar met de concrete reden. Een dergelijk instrument wordt niet
stilzwijgend aan een willekeurig aandeel gekoppeld. Automatische valutaomrekening
is nog niet beschikbaar; bronbedragen worden niet als een andere valuta geboekt.
Met **Automatisch opnieuw koppelen** probeer je openstaande koppelingen opnieuw.
Onder **Importgeschiedenis → Voorbeeld openen** kun je ook bestaande previews
hervatten; een nieuwe CSV of API-download is niet nodig. Alles blijft admin-only.
Schema blijft 7; mappinggegevens gebruiken de bestaande preview- en cacheopslag.

### Valuta en uitgebreidere import (0.7.0)

**Valuta** is beschikbaar voor admin en basic. Je kunt een bedrag, bronvaluta,
doelvaluta (bijvoorbeeld EUR) en datum kiezen. De pagina toont de berekende waarde,
factor, gevraagde datum en werkelijke koersdatum. Het overzicht toont alle valuta
die de dienst levert plus GBX; niet iedere valuta heeft op iedere historische datum
een koers. De historie is per valuta te bekijken (laatste 500 opgeslagen observaties).

De [Frankfurter v2-API](https://frankfurter.dev/) levert dagelijkse referentiekoersen
uit officiële bronnen, standaard gecombineerd over providers. Dit zijn **geen live
FX-koersen of gegarandeerde Trading 212-afrekenkoersen**. Spread, brokerkosten en
belasting worden niet alsnog verwerkt. De bron staat bij de koers en omrekening.
Bij niet-handelsdagen kan een eerdere observatie nodig zijn; die datum wordt expliciet
getoond. De app gebruikt geen toekomstige koers of een ongemerkte 1:1-verhouding.

Alle positieve API-antwoorden en dagobservaties worden in SQLite bewaard. Koersen
worden met Decimal berekend; bestaande dagobservaties worden niet stilzwijgend
vervangen. De achtergrondtaak controleert elke 6 uur op nieuwe daggegevens. De
valutalijst heeft 7 dagen cache; historische gegevens blijven lokaal beschikbaar.
Importen halen ontbrekende historie per jaar en alleen voor benodigde valuta op.
Ontbrekende of ongeldige koersantwoorden worden niet langdurig als succes gecachet.

**GBX is Britse pence: 100 GBX = 1 GBP.** Yahoo's `GBp` en Trading 212 `GBX` worden
als pence behandeld, inclusief aandelenkoersen en historie. London en Swiss zijn
nu ondersteund. Voor VWCE, VUSA, VFEA en EQGB gebruikt de resolver daarnaast
ISIN-tabellen uit de issuerdocumentatie. De actuele beurs en valuta worden nog
steeds bij Yahoo gecontroleerd. Dit voorkomt afhankelijkheid van onvolledige
zoekresultaten of een willekeurige keuze uit verschillende fondsen.

Bij een gecontroleerde notering met een andere valuta worden prijs per aandeel
en/of dividend op de transactiedatum naar de noteringsvaluta omgerekend. De originele
CSV-regel, bronvaluta, origineel bedrag, omgerekend bedrag, factor, koersdatum en bron
blijven bewaard. **Valuta → Omrekeningen bij imports** toont deze registratie.
Een dividend dat in EUR is ontvangen kan zo bij een USD-positie worden geboekt.
Een ontbrekende historische koers blokkeert de hele import; er wordt niets half geboekt.
Bestaande bron-ID's blijven de deduplicatie bepalen, ook na herstart en herstel.

Na bijwerken: open bij **Imports → Importgeschiedenis** je bestaande voorbeeld en
laat de automatische koppeling opnieuw lopen. Er is geen nieuwe brokerexport nodig.
Bestaande financiële boekingen worden niet automatisch opnieuw omgerekend.
Schema **8** voegt valutametadata, dagkoersen, historische dekking en importomrekeningen
toe. De normale transactionele migratie maakt vooraf een veiligheidsback-up; de
nieuwe tabellen zitten in SQLite-back-ups en gevalideerd herstel. Gebruikers en
API-sleutels blijven behouden.

Bronnen voor de ISIN-hints: [Vanguard All-World](https://fund-docs.vanguard.com/FTSE_All-World_UCITS_ETF_USD_Accumulating_9679_NETH_INT_DU.pdf),
[Vanguard S&P 500](https://fund-docs.vanguard.com/SandP_500_UCITS_ETF_USD_Distributing_9503_EU_INT_EN.pdf),
[Vanguard Emerging Markets](https://fund-docs.vanguard.com/FTSE_Emerging_Markets_UCITS_ETF_USD_Accumulating_9678_EU_INT_UK_EN.pdf)
en [London Stock Exchange EQGB](https://www.londonstockexchange.com/stock/EQGB/invesco/company-page).

### Importknop (0.7.1)

Na de automatische koppeling is de opslagknop bedienbaar. Eventuele fouten per bronregel of ontbrekende koppelingen staan direct bij de knop. De bevestiging slaat deze controles niet over; corrigeer gemelde bronfouten voordat je opnieuw importeert. Fouten bij het opslaan verschijnen ook naast de knop. Schema blijft 8.

### Automatische koppeling MO en SOF (0.7.2)

Euronext Brussel wordt nu ondersteund. Gecontroleerde ISIN-koppelingen voor Altria (US02209S1033, MO in USD) en Sofina (BE0003717312, SOF.BR in EUR) werken ook bij onvolledige zoekresultaten. Afwijkende bronvaluta wordt via de bestaande historische omrekening verwerkt. Open je bestaande importvoorbeeld en klik Automatisch opnieuw koppelen. Schema blijft 8.

Noteringsbronnen: [Altria NYSE MO](https://investor.altria.com/stock-performance/default.aspx), [Altria ISIN](https://live.euronext.com/nl/product/equities/US02209S1033-BGEM/market-information), [Sofina ISIN en Brussel](https://live.euronext.com/en/product/equities/BE0003717312-XBRU).

### Dividend zonder aankoophistorie (0.7.3)

Een gecontroleerde dividendontvangst kan worden geimporteerd als de voorafgaande aankoop niet in de gekozen periode of lokale historie staat. De ontvangst blijft bij het gekozen brokeraccount, met een melding bij Dividend en in het importresultaat. Er wordt geen aankoop, aantal of kostprijs aangemaakt. De ontvangst staat in Dividend en Rapporten; een totaalrendement op een positie vereist aankoophistorie. Automatische beurskoppeling, historische valutaomrekening, deduplicatie en volledige rollback blijven gelden. Bestaande voorbeelden kunnen opnieuw worden opgeslagen. Schema blijft 8.

### Blijvende aandelenkoppelingen (0.8.0)

Open **Imports > Aandelenkoppelingen beheren** (alleen admin). De subpagina toont alle bekende en openstaande instrumenten uit eerdere importvoorbeelden, per brokeraccount, ISIN/bronticker en bronvaluta. De lijst en lokaal zoeken gebruiken geen koersdienst. Bekende koppelingen blijven in SQLite zonder vervaldatum bewaard, ook na herstart. Bestaande opgeslagen previewkoppelingen worden lokaal overgenomen.

Kies **Corrigeren** of **Koppelen**, vul de juiste Yahoo-koersticker in en klik **Notering controleren**. Beurs en noteringsvaluta worden opgehaald; **Koppeling opslaan** controleert dat ze bij die notering horen. Controleer zelf ook de identiteit/ISIN van het gekozen aandeel. Een foutieve beurs of valuta wordt niet opgeslagen. Een manuele correctie wordt niet overschreven door automatisch koppelen. Open je importvoorbeeld daarna opnieuw.

Correcties gelden voor openstaande en volgende imports. Eerder geboekte transacties, oorspronkelijke CSV-regels en de gebruikte omrekeningen blijven als administratie behouden; bestaande boekingen worden niet stilzwijgend van aandeel of valuta veranderd. Het register is geen functie om oude boekingen opnieuw te waarderen.

Dezelfde eenduidige ISIN-koppeling kan voor een andere bronvaluta worden hergebruikt; de historische omrekening blijft gelden. Bij een Yahoo 429/503 stopt het automatisch koppelen en geldt een opgeslagen wachttijd (Retry-After, minimaal 60 seconden). Reeds opgeslagen koppelingen blijven bruikbaar. Nieuwe instrumenten kunnen nog koersaanvragen nodig hebben.

Schema 9 voegt het koppelingenregister toe, met automatische migratie-back-up en ondersteuning in back-up/herstel. De regels met **Dividend (Return of capital manufactured payment)** blijven expliciet geblokkeerd: kapitaalterugbetaling is geen gewoon dividend en wordt niet stilzwijgend als winst geboekt. Dit is een apart probleem, geen API-limiet. Een oudere importperiode of beheer van beurskoppelingen lost dat transactietype niet op.

### Importeren met beoordeling achteraf (0.9.0)

Klik **Import definitief opslaan**, ook als sommige noteringen of bronregels nog niet kloppen. Geldige regels worden opgeslagen. Ontbrekende koppelingen, onbekende acties, ontbrekende wisselkoersen, ongeldige verkopen en bron-ID-conflicten komen duurzaam in **Imports > Te beoordelen**. Een import met uitsluitend fouten wordt ook gestart en levert een beoordelingslijst op. Het bestand moet wel een leesbare Trading 212 CSV zijn.

Per regel kies je **Opnieuw proberen**, **Kapitaalterugbetaling**, **Ontvangen dividend**, **Aankoop**, **Verkoop** of **Bewust overslaan**. Er wordt niets geschat: de gekozen classificatie gebruikt de oorspronkelijke bedragen en datum; ontbreken noodzakelijke waarden, dan blijft de regel apart staan. Herstel ontbrekende noteringen bij Aandelenkoppelingen en probeer de regels daarna opnieuw. Een keuze verwerkt ook andere inmiddels opgeloste regels in dezelfde import opnieuw. Reeds geboekte regels worden herkend en niet dubbel opgeslagen.

Kapitaalterugbetalingen (zoals Return of capital manufactured payment) worden pas na jouw keuze apart opgeslagen, in de bronvaluta. Ze staan onder Te beoordelen in een afzonderlijk overzicht en tellen niet als dividendwinst. Er wordt geen automatische fiscale kostprijscorrectie gedaan. De oorspronkelijke bronregel en keuze blijven bewaard. Bewust overslaan bewaart de bronregel eveneens; bestaande boekingen worden nooit overschreven.

De import is per regel transactioneel: een mislukte regel laat geen aankoop, dividend, omrekening of importregistratie achter. Andere geldige regels mogen wel slagen. Imports met resterende regels staan in de geschiedenis als **Deels verwerkt - beoordeling nodig**. De beheerpagina toont maximaal 2.000 beoordelingen (openstaande eerst) en 500 kapitaalterugbetalingen; alle gegevens blijven in SQLite bewaard. Alleen admins hebben toegang.

Schema 10 voegt de beoordelingslijst en kapitaalterugbetalingen toe, met automatische migratie-back-up, herstelvalidatie en ondersteuning voor oudere back-ups. Bestaande openstaande importvoorbeelden kunnen opnieuw worden gestart zonder nieuwe brokerexport.

Madrid en Amerikaanse OTC-noteringen worden nu ondersteund. De ISIN-koppelingen voor SAB (ES0113860A34), UNI (ES0180907000) en TCEHY (US88032Q1094) worden via actuele koersmetadata gecontroleerd.

Noteringsbronnen: [Banco Sabadell bij BME](https://www.bolsasymercados.es/en/bme-exchange/prices-and-markets/shares/detail.banco-de-sabadell-es0113860a34.html), [Unicaja ISIN](https://www.unicajabanco.com/content/dam/unicaja/unicaja-corporacion/documentos-corporacion/junta-general-de-accionistas/2021-extraordinaria/2021-extraordinaria-documento-conforme-reglamento-ue-en.pdf), [Tencent ADR bij Citi](https://depositaryreceipts.citi.com/adr/notices/pgm_dispCA.aspx?cusip=88032Q109&pageId=15&subpageID=112).

### Nieuw Home-overzicht (0.10.0)

Home opent met het portefeuilletotaal in EUR (of de eerste aanwezige valuta). Valutaknoppen houden bedragen gescheiden; de kerncijfers tonen marktwaarde, openstaande kostprijs, totale winst en dividend dat aan deze posities gekoppeld is. Ontbrekende koersen worden expliciet gemeld. Er wordt geen automatische EUR-conversie verondersteld.

Gebruik de positielijst om lokaal te zoeken op bedrijf, ticker, beurs of brokeraccount. Filter open/gesloten posities, ontbrekende koersen en positieve/negatieve resultaten; sorteer op waarde, weging, naam of winstpercentage. De lijst toont 25 regels per pagina. **Bekijken** opent de grafiek van die positie. Selecteer maximaal zes posities met de selectievakjes om ze gericht te vergelijken; de standaardgrafiek tekent niet meer alle honderd lijnen tegelijk.

Grootste posities toont de vijf grootste bekende marktwaarden binnen de gekozen valuta. Beste/zwakste resultaat toont winst sinds aankoop gedeeld door de totale oorspronkelijke inleg, inclusief gekoppeld dividend. Dit is geen tijdgewogen rendement en geen rendement over de geselecteerde grafiekperiode. Een periodeknop verandert alleen de getoonde datums.

De grafiek vult de beschikbare breedte en ondersteunt muis en pijltjestoetsen. Via de legenda kun je lijnen aan/uit zetten. Dagwaarden worden pas opgebouwd bij uitklappen, per 250 regels, zodat lange historie en veel posities de pagina niet met duizenden tabelregels belasten. Zoeken, sorteren en selectie gebruiken de reeds opgehaalde gegevens en doen geen extra koersaanvragen. Schema blijft 10; bestaande gegevens en back-ups blijven bruikbaar.
