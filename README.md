# Home Invest voor Home Assistant

Experimentele versie (0.35.0). Draait volledig als Home Assistant-app
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

Home Invest houdt aankopen, verkopen, dividend en koershistorie bij in SQLite.
Brokeraccounts zijn afzonderlijke portefeuillerekeningen; gebruikersaccounts regelen
toegang tot de app. Wijzigen en instellen gebeurt in pop-ups; Home opent direct met het portefeuilleoverzicht.

- **Home**: overzicht per valuta, posities zoeken/filteren en maximaal zes posities vergelijken. Via **Dashboard aanpassen** krijgt ieder onderdeel op Home zelf een versleepgreep en tandwiel. Verplaats de tien modules direct en kies per onderdeel zichtbaarheid en breedte. De indeling blijft per gebruiker en profiel bewaard.
- **Transacties**: alle boekingen bekijken, zoeken en als admin wijzigen, met wijzigingshistorie. Subpagina’s voor dividend en splitsingen/omzettingen.
- **Aandelen**: posities en transacties bekijken; handmatig aankopen toevoegen.
- **Dividend**: netto ontvangen dividend boeken en bekijken.
- **Instellingen → Valuta**: historische omrekening en opgeslagen dagreferentiekoersen.
- **Rapporten**: dividend per maand en portefeuillestand.
- **Imports** (admin): eigen pagina’s voor Trading 212 CSV/API, Trade Republic en Revolut CSV, plus Exporteren, API-instellingen, beurskoppelingen en regels ter beoordeling.
- **Instellingen** (admin): accounts, beveiliging, back-ups en versiecontrole.
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
en geboekte transacties blijven behouden. Kosten, cashmutaties en valutawissels worden
niet in het portefeuillerendement verwerkt.

## Opslag en back-ups

De database en instellingen staan in de app-datafolder. Appversie **0.35.0** gebruikt
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

Landenverdeling heeft een interactieve wereldkaart met lokale vlaggen, percentages en een Europaweergave. Rapporten tonen alleen relevante cijfers; de algemene waarde-/winstkaarten staan op Portefeuilleoverzicht, met Rendementsoverzicht direct daaronder in het menu.

### Export en Revolut

Open **Imports → Exporteren** en kies CSV of PDF. De export bevat de transacties, dividend en kapitaalterugbetalingen van de geselecteerde brokerrekening (of alle accounts), met bronvaluta.

Open **Imports → Revolut** en upload de Engelstalige beleggings-CSV, niet het bankrekeningafschrift. Zowel het formaat met Ticker, Price per share en Total Amount als dat met Reference, CCY, Price/share en Net Amt. wordt herkend. Aankopen, verkopen en dividend worden verwerkt; onbekende acties blijven ter beoordeling. Bewaar en importeer de volledige historie. Regels zonder bron-ID worden op hun inhoud vergeleken; identieke regels binnen één bestand vereisen beoordeling.
