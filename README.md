# Home Invest voor Home Assistant

Experimentele versie (0.41.2). Draait volledig als Home Assistant-app
(voorheen add-on), met een dashboard via de Home Assistant-zijbalk en eigen
SQLite-database. Geen externe hosting, CDN of browserbibliotheken nodig.

## Passkeys (v0.58.0)

Naast het bestaande wachtwoord kun je op een ondersteund apparaat een **passkey**
registreren. Meld je eerst aan met je eigen account, open **Mijn account** en
gebruik **Passkeys → Passkey toevoegen**. Bevestig met je huidige wachtwoord,
geef de passkey een herkenbare naam en volg de beveiligingsprompt van je apparaat.
De knop **Inloggen met passkey** verschijnt op het inlogscherm op apparaten met
browserondersteuning. Beheerders en gewone gebruikers hebben hun eigen passkeys;
meerdere passkeys per account zijn mogelijk, maximaal tien.

Deze implementatie gebruikt de WebAuthn-standaard: de server verifieert elke
eenmalige uitdaging en cryptografische handtekening. Alleen de publieke sleutel,
teller en herkomst worden in SQLite bewaard. Er worden geen biometrische gegevens
naar Home Invest gestuurd. Je wachtwoord blijft als reserve beschikbaar en is
ook nodig om passkeys toe te voegen of te verwijderen.

**Vereisten en beperkingen:** open Home Invest via een vertrouwde HTTPS-hostnaam
(of localhost voor ontwikkeling); een gewoon HTTP-adres op je lokale IP-adres
ondersteunt geen passkeys. Een passkey wordt gekoppeld aan de volledige oorsprong
(hostnaam) waarop hij is geregistreerd. Als je via een ander Home Assistant-domein
werkt, kan een nieuwe registratie nodig zijn. Bij gebruik als iframe binnen
Home Assistant hangt ondersteuning ook af van de browser en het iframebeleid van
Home Assistant. Open Home Assistant zo nodig in een reguliere browser. Test eerst
een passkey voordat je op passkeys vertrouwt voor aanmelden. Houd je wachtwoord
altijd beschikbaar en controleer of je herstelback-up ook de nieuwe SQLite-tabel
bevat.

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

Home Invest houdt aankopen, verkopen, dividend en koershistorie bij in SQLite.
Brokeraccounts zijn afzonderlijke portefeuillerekeningen; gebruikersaccounts regelen
toegang tot de app. Wijzigen en instellen gebeurt in pop-ups; Home opent direct met het portefeuilleoverzicht.

- **Home**: overzicht per valuta, posities zoeken/filteren en maximaal zes posities vergelijken. Via **Dashboard aanpassen** krijgt ieder onderdeel op Home zelf een versleepgreep en tandwiel. Verplaats de tien modules direct en kies per onderdeel zichtbaarheid en breedte. De indeling blijft per gebruiker en profiel bewaard.
- **Transacties**: alle boekingen bekijken, zoeken en als admin wijzigen, inclusief brokeraccount, kosten, btw en andere belastingen, met wijzigingshistorie. Subpagina’s voor dividend en splitsingen/omzettingen.
- **Aandelen**: posities en transacties bekijken; handmatig aankopen toevoegen.
- **Dividend**: netto ontvangen dividend boeken en bekijken.
- **Instellingen → Valuta**: historische omrekening en opgeslagen dagreferentiekoersen.
- **Rapporten**: portefeuille, rendement, dividend, kosten en belastingen.
- **Imports** (admin): een overzicht met brokerlogo’s en eigen stappenhandleidingen met schermafbeeldingen voor Trading 212 CSV/API, Trade Republic en Revolut CSV. Importvoorbeeld, importgeschiedenis, exporteren, API-instellingen, beurskoppelingen en beoordelingen hebben aparte pagina’s.
- **Instellingen** (admin): accounts, beveiliging, back-ups en versiecontrole. Bij **Back-ups en updates** staan alle lokale back-ups (ook veiligheidskopieën in submappen) en lokale updatebestanden met grootte, downloaden en verwijderen. SQLite-back-ups kunnen na bevestiging rechtstreeks worden hersteld; vooraf wordt een veiligheidskopie gemaakt. Home Assistant beheert installatiepakketten en eigen back-ups afzonderlijk.
- **Instellingen → Logs** (admin): afgeschermde foutdetails en Log-ID zoeken.

Koersen komen van Yahoo Finance en kunnen vertraagd of tijdelijk onbeschikbaar zijn. Apollo LU3170240538 in EUR gebruikt de openbare DivvyDiary-koers, zonder vermelde koersdatum; de app toont het ophaalmoment. Bij Instellingen → TMX omboeken naar TDT kun je de VanEck-fusie per brokeraccount verwerken met behoud van kostprijs en een herstelback-up.
Bedragen in verschillende valuta blijven gescheiden. De app voert geen orders uit. Home gebruikt opgeslagen databasegegevens en een blijvende overzichtcache; koersen worden op de achtergrond ververst.

## Waarden in je Home Assistant-dashboard

Open in Home Invest **Instellingen → Home Assistant-sensoren**. Daar staan de actuele
waarde per valuta, het totaal omgerekend naar euro en de bijbehorende REST-configuratie.
Stel in de Home Assistant-appconfiguratie een `home_assistant_token` in (32–128 letters,
cijfers, streepjes of underscores), schakel netwerkpoort `8100/tcp` in en herstart de app.
Neem vervolgens de getoonde sensorconfiguratie en twee secrets over in Home Assistant.
De sensoren verversen iedere minuut via één lokale aanvraag en gebruiken opgeslagen
koersen. De koppeling staat standaard uit; het dashboard blijft via ingress bereikbaar.

`127.0.0.1` is een lokaal ontwikkelvoorbeeld op je eigen computer. Voor echte sensoren
gebruik je het lokale adres van je Home Assistant-apparaat. De waarden betreffen
beleggingen over alle brokeraccounts, zonder los brokersaldo of uitgekeerd dividend.
Ontbrekende koersen maken de betreffende sensor onbekend; er wordt niets geschat.

## Trading 212 importeren

1. Maak bij **Instellingen → Brokeraccounts** een Trading 212-rekening aan.
2. Upload bij **Imports** een Engelstalige History CSV, of verbind de API met alleen
   rapportrechten. Voor de API moet gebruikersbeveiliging aanstaan.
3. Kies de volledige transactieperiode, controleer het voorbeeld en de beurskoppelingen.
4. Klik **Import definitief opslaan**. Geldige regels worden geboekt; ongeldige regels
   blijven bewaard onder **Imports → Te beoordelen**. Overlappende imports worden
   per brokeraccount op bron-ID gecontroleerd.
5. Herstel ontbrekende koppelingen of historie en kies **Opnieuw proberen**.

Ondersteund: aankopen, verkopen, dividend, kapitaalterugbetalingen en aandelensplitsingen.
**Dividend (Return of capital manufactured payment)** wordt automatisch apart opgeslagen
in de bronvaluta en telt niet als dividendwinst.
**Stock split open** stelt het nieuwe totale aantal in met behoud van kostprijs,
inleg en gerealiseerde winst. **Stock split close** controleert het oude aantal als
beide regels op hetzelfde tijdstip in het bestand staan. Voorafgaand bezit moet bekend zijn.
Een losse close of ongeldige splitsing blijft ter beoordeling staan.

Eerder afgewezen regels kun je na bijwerken opnieuw proberen; eerdere handmatige keuzes
en geboekte transacties blijven behouden. Expliciete kosten en belastingen worden apart
geboekt en in het Rendementsoverzicht verwerkt. Cashmutaties blijven buiten de portefeuille.

## Opslag en back-ups

De database en instellingen staan in de app-datafolder. Appversie **0.41.2** gebruikt
databaseschema **19**. Upgrades maken vooraf een consistente back-up en voeren alleen
ontbrekende migraties transactioneel uit. Bestaande aankopen, dividend en historie blijven
behouden. Neem voor opgeslagen API-verbindingen de volledige app op in een Home Assistant-back-up.

Onder **Instellingen → Portefeuillegegevens verwijderen** wis je alles of één
brokeraccount. Controleer het overzicht en typ VERWIJDEREN. De app bewaart eerst een
herstelback-up die je daarna kunt downloaden. Accounts en beveiliging blijven behouden.
Verwijderde imports kunnen daarna opnieuw worden ingelezen.

Gebruikersdata, back-ups en API-sleutels horen niet in deze repository.

## Documentatie en ontwikkeling

- [Uitgebreide handleiding](portfolio/DOCS.md): installatie, gebruik, API, beveiliging,
  opslag en ontwikkelinstructies.
- [Changelog](CHANGELOG.md): versiegeschiedenis; ook bijgehouden in het [Home Assistant app-changelog](portfolio/CHANGELOG.md).
- [Projectafspraken](AGENTS.md): afspraken voor onderhoud.

Tests uitvoeren vanuit de repository: python -m unittest discover -s tests.
De grafiek- en Home-controles staan in tests/test_chart.cjs en tests/test_home.cjs.

De app ondersteunt Nederlands, Engels en Spaans. Kies je taal bij de eerste start; klik onderaan het menu op je gebruikersnaam voor **Mijn account** met **Taal / Language / Idioma**, **Account aanpassen** en **Uitloggen**. Met loginaccounts wordt de keuze per gebruiker bewaard.

## Rapporten

Kies de huidige portefeuille, resultaat per aandeel, dividend per maand of dividend per aandeel. Filter op brokeraccount en valuta. De jaarkeuze geldt voor dividendrapporten; resultaat en portefeuille tonen de actuele stand inclusief alle geboekte dividenden. Bedragen blijven gescheiden per valuta.

Rapporten slaan regels met ontbrekende of ongeldige gegevens over en tonen hoeveel regels niet zijn meegenomen. Totalen gelden alleen voor de meegenomen regels. Een dividenduitkering kan worden meegenomen zonder actuele aandelenkoers. De opgeslagen transacties blijven behouden.

Het rapportencentrum bevat tien analyses met interactieve grafieken, waaronder waardeontwikkeling, spreiding, resultaatopbouw, dividendkalender en sector- en landenverdeling. Open **Onderliggende cijfers** voor de bijbehorende tabel.

Rapporten openen als afzonderlijke pagina via het uitklapmenu links. De dividendkalender toont per aandeel de betaaldatum en ontvangen of geschatte bedragen. Kies tot vijf jaar vooruit en 0%, 3%, 5% of 10% jaarlijkse groei. Standaard is 3% een scenario-aanname, geen gemeten groei. De basis is het netto ontvangen bedrag in de afgelopen twaalf maanden voor nog open posities, zonder correctie voor gewijzigd bezit, belasting of toekomstige valuta. Datums zijn indicatief; aangekondigde uitkeringen zijn niet gekoppeld.

De dividendkalender heeft een maandraster met navigatie en een detailagenda. Klik op een betaaldag om bedragen, aandelen en de basis van schattingen te zien. Op mobiel staan de details onder de kalender. Rapporten benutten de volledige beschikbare breedte.

Rapporten starten met een gecombineerd totaal in EUR en tonen daarna de geselecteerde bronvaluta afzonderlijk. Ook filters voor broker en bronvaluta gelden voor het totaal. Bedragen worden op de server met opgeslagen, gedateerde wisselkoersen omgerekend; ontbrekende omrekeningen worden vermeld. Onderliggende cijfers bevatten het totaal en de uitsplitsing als afzonderlijke regels en mogen niet bij elkaar worden opgeteld.

## Demoprofiel

Open **Mijn account → Profiel kiezen** om te wisselen tussen je eigen portefeuille en de demo. Zonder loginaccount kun je de keuze ook maken in de taalpopup. De demo toont 10 brokers en 150 aandelen in 10 valuta’s. Transacties, dividend en daghistorie zijn fictieve voorbeelden; actuele koersen worden op de achtergrond bij Yahoo Finance opgehaald en kunnen vertraagd of onbeschikbaar zijn. Bij een fout blijft de vorige koers zichtbaar, aanvankelijk de fictieve demokoers (bron DEMO).

De eigen portefeuille blijft in `data/portfolio.sqlite3`; de demo gebruikt `data/demo/portfolio.sqlite3` (in Home Assistant `/data/demo/portfolio.sqlite3`). Loginaccounts en sessies blijven van de eigen installatie. De demo wordt op de achtergrond voorbereid en hergebruikt, zonder dagelijkse herbouw. Succesvolle providerantwoorden worden gecachet; verversen gebeurt op zijn vroegst na vijf minuten en kan bij veel aandelen langer duren. De gekozen portefeuille staat in het pagina-adres en blijft bij herladen behouden. De demo is alleen-lezen.

Landenverdeling opent zonder bovenste header met een paginabrede interactieve wereldkaart en daaronder de landentabel met marktwaarde en weging. Lokale vlaggen, percentages en de Europaweergave blijven beschikbaar. Rapporten tonen alleen relevante cijfers; de algemene waarde-/winstkaarten staan op Portefeuilleoverzicht, met Rendementsoverzicht direct daaronder in het menu.

### Export en Revolut

Open **Imports → Exporteren** en kies CSV of PDF. De export bevat transacties, dividend, kapitaalterugbetalingen en kostenboekingen van de geselecteerde brokerrekening (of alle accounts), met bronvaluta.

Open **Imports → Revolut** en upload de Engelstalige beleggings-CSV, niet het bankrekeningafschrift. Zowel het formaat met Ticker, Price per share en Total Amount als dat met Reference, CCY, Price/share en Net Amt. wordt herkend. Aankopen, verkopen en dividend worden verwerkt; onbekende acties blijven ter beoordeling. Bewaar en importeer de volledige historie. Regels zonder bron-ID worden op hun inhoud vergeleken; identieke regels binnen één bestand vereisen beoordeling.

## Wensen & bugs

Meldingen worden binnen Home Invest ingediend en gevolgd; gebruikers hebben geen GitHub-account nodig. De beheerder stelt `feedback_service_url` in de Home Assistant-appconfiguratie in (bijvoorbeeld `https://meldingen.home-invest.nl`) en activeert de installatie via **Wensen & bugs → Meldservice activeren** met een eenmalige code. Zonder deze inrichting staat verzenden uit. Per installatie geldt een limiet van vijf meldingen per 24 uur. Alleen de bewust ingevulde tekst en de appversie worden verstuurd; meldingen worden openbaar op GitHub.

De aparte centrale container wordt in Coolify gebouwd met `feedback_service/Dockerfile` en buildcontext `/`. Zie [installatie, GitHub App en beheer](feedback_service/README.md) voor Coolify.

De lokale wachtrij en installatiegegevens staan versleuteld in de aparte map `feedback/` in de app-datafolder, buiten het portefeuilledatabestand. Ze blijven behouden bij portefeuilleherstel; een volledige Home Assistant-appback-up is nodig om de meldverbinding mee te herstellen. Versturen wordt automatisch hervat. Bij een onduidelijke GitHub-verzenduitkomst controleert de centrale beheerder de melding om dubbele issues te voorkomen.

Via **Over ons** vind je alle gebruikte bronnen. Op de aandelendetailpagina staan aanvullende jaarcijfers van Defeat Beta voor ondersteunde Amerikaanse noteringen, met rapportagevaluta en peildata.

### Kosten en belastingen

Bij **Rapporten → Kosten en belastingen** en **Belastingoverzicht** staan bekende
kosten, btw en inhoudingen per jaar, brokeraccount en bronvaluta, met een EUR-totaal.
Het **Rendementsoverzicht** trekt aanvullende kosten af; reeds netto verwerkte
inhoudingen tellen niet dubbel. De aandelenkostprijs wordt niet herschreven.
Ontbrekende kosten zijn onbekend, niet nul. Voeg bronbedragen toe via de pop-up of het
CSV-sjabloon. Een afzonderlijk Revolut-kostenrapport wordt niet als transactie-CSV gelezen.
Zie DOCS voor ondersteunde velden en het voorkomen van dubbeltellingen.

Handmatige aankopen en verkopen hebben in dezelfde pop-up velden voor kosten exclusief btw,
btw en een optionele eigen kostenvaluta. Transactie en kosten worden samen opgeslagen.

Bij een handmatige transactie in een andere valuta kun je ook de prijs per aandeel in EUR
invullen. Het formulier rekent om op transactiedatum en toont de gebruikte koersdatum.

Portefeuilleoverzicht staat bovenaan de rapportenlijst en toont standaard één gecombineerd EUR-dashboard met vier kerncijfers en zes grafieken. Filter op broker, bronvaluta, aandeel, sector of open/gesloten posities. Zet **Uitsplitsing per valuta tonen** aan voor afzonderlijke bronvaluta naast het totaal.

Op **Je aandelen** geven sectoren met symbolen en een korte uitleg hun betekenis weer. De interactieve landenkaart toont aantallen open beursnoteringen en hun weging, met een wereld- en Europaweergave. De kaart telt iedere open beursnotering één keer; dit is geen verdeling naar marktwaarde.

ETF's hebben op de detailpagina **Onderliggende beleggingen**. Via **Instellingen > Taken** kan een beheerder gratis de samenstelling voor alle ETF-noteringen van alle brokeraccounts ophalen. Invesco, VanEck, Vanguard en iShares worden automatisch herkend via hun officiële catalogi op basis van ISIN, ticker of eenduidige naam. Hiervoor is geen betaalde dienst, API-sleutel of zelf ingevulde URL nodig. EXV1.DE en IWDA.AS behouden hun vooraf ingestelde iShares-bron. Start alle fondsen, alleen ontbrekende/verouderde samenstellingen of mislukte/onderbroken taken. De taak loopt op de achtergrond; voortgang en fouten blijven per fonds zichtbaar. Stoppen wacht de lopende aanvraag af. Na een app-herstart moet een onderbroken taak opnieuw gestart worden. Het openen van de pagina doet geen externe aanvragen.

De gratis bronnen dekken niet elk fonds of elke classificatie. Bij Invesco ontbreken soms sector en land; dat blijft zichtbaar als niet ingedeeld. Niet eenduidig herkende fondsen krijgen een melding. Als alternatief kan **ETF-samenstelling beheren** nog steeds een officiële productpagina/CSV-bron of volledige CSV importeren. CSV-kolommen: Naam, Weging (%), optioneel Sector, Land, Symbool, ISIN, Type en Categorie. Engelse en Duitse iShares-kolommen worden herkend. XLSX/PDF worden niet rechtstreeks ingelezen.

De app bewaart alle bronregels, ook contanten, derivaten en negatieve wegingen. Een bron met onvolledige dekking wordt niet opgehoogd tot 100%; het ontbrekende deel blijft **ETF niet uitgesplitst**. Een peildatum ouder dan 14 dagen wordt gemeld. Gekoppelde bronnen worden maximaal dagelijks bijgewerkt; fouten behouden de vorige samenstelling en hebben een wachttijd. CSV-import zonder bron-URL wordt handmatig bijgewerkt. Dagelijkse controle vereist dat de automatische koersverversing draait.

Rapporten rekenen de actuele ETF-marktwaarde naar onderliggende beleggingen door voor spreiding, sectoren en landen, met behoud van het gecombineerde EUR-totaal. Het uitklapbare ETF-blok is in ieder rapport beschikbaar. Winst, belasting, kosten, dividend en historie blijven gebaseerd op echte ETF-boekingen: de huidige samenstelling wordt niet als historische winst van de onderliggende aandelen gepresenteerd. Bronwegingen zijn percentages van fondsvermogen, geen gegarandeerde economische blootstelling bij derivaten of synthetische fondsen. ETF-in-ETF wordt één niveau uitgesplitst.

### ETF-beleggingen en Home-grafiek

Klik in een ETF-samenstelling of rapport op een belegging om de aandeelpagina te openen. Die vermeldt dat de belegging via de ETF wordt aangehouden, met weging en peildatum. Dit maakt geen rechtstreekse positie of boeking aan. Bedrijfsprofielen worden alleen gekoppeld bij een gecontroleerde identiteit; ontbrekende informatie blijft zichtbaar.

Home toont standaard het resultaat sinds aankoop als percentage van de totale aankoopinleg. Groen is positief en rood negatief. Kies **Grafiekmeting** voor de bestaande marktwaarde/kostprijsgrafiek. Periodeknoppen kiezen de getoonde dagwaarden; 1D is een dagwaarde, geen intraday-koers. De grafiek is geen tijdgewogen rendement van de gekozen periode. Handelsvolume voor een portefeuille wordt niet gesimuleerd.

Bij ontbrekende koersen toont de resultaatgrafiek het bekende deel. Winst en aankoopinleg komen per dag van dezelfde posities. De grafiek vermeldt het ontbrekende aantal; het getoonde deel kan per dag verschillen. Dit is geen volledig portefeuillerendement. Dagen waarop geen resultaat kan worden berekend blijven leeg.

Het EUR-overzicht laadt eerst de totalen en daarna de historische grafiek op de achtergrond. Een trage grafiek blokkeert de pagina niet. Bij een grafiekfout blijven de totalen staan en kun je **Grafiek opnieuw laden** kiezen. Ongewijzigde portefeuillegegevens en berekende historie worden hergebruikt.

Onder **Instellingen > Statistieken** zien admins het CPU- en geheugenverbruik van de app, het containergeheugen (indien beschikbaar), de overzichtcache en opslag. CPU 100% staat voor één processorkern. De pagina meet elke 15 seconden zolang zij zichtbaar is; opslag wordt maximaal elke 30 seconden gemeten. De databasecache is onderdeel van het databasebestand, geen extra opslag bovenop dat bestand. Herbruikbare databaseruimte blijft beschikbaar voor volgende schrijfacties.

De statistiekenpagina bevat ook diagnostiek voor geheugenpieken, actieve berekeningen, cache-afwijzingen en berekeningstijden. **Diagnose downloaden** bewaart deze technische metingen en aantallen lokaal als JSON, zonder posities, bedragen, accountnamen of sleutels. Deel dit bestand bij aanhoudend hoog verbruik.

Bij transacties met een jaartal vóór 1900 voorkomt de app dat er eeuwen aan dagwaarden worden opgebouwd. De boekingen blijven behouden. Home en Statistieken waarschuwen en linken naar de betrokken transacties; controleer en corrigeer de datum via de bestaande transactiepopup. De app gokt niet welke datum bedoeld was.

**Instellingen > Gegevens opschonen** opent een controlevenster. De app maakt vóór het opschonen een volledige herstelback-up. Per beursnotering en dag kan alleen de laatste koerswaarneming worden bewaard; dagelijkse koershistorie en alle boekingen blijven behouden. Cacheopschoning bewaart bronwachttijden, ETF-taakstatus en Trading 212-brongegevens. Bij back-upopschoning blijven de vijf nieuwste kopieën staan, inclusief de veiligheidskopie; ook toekomstige app-back-ups gebruiken dan die limiet. Opschonen wacht niet op achtergrondtaken: probeer het opnieuw wanneer de lopende taak gereed is.
