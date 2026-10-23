## 0.21.1

- Blijf 48 uur ingelogd; bij gebruik worden de sessie en cookie automatisch verlengd.
- Sessies blijven behouden na een appherstart en worden bij uitloggen, accountwijzigingen en herstel ingetrokken.
- Databaseversie 16 voegt blijvende sessies toe met uitsluitend gehashte sessiesleutels.

## 0.16.2

## 0.21.0
- Dividend krijgt Alle valuta’s in euro voor kerncijfers, grafieken, kalender, uitbetalers en betalingen. Historische bedragen worden op betaaldatum omgerekend; de verwachting houdt de huidige wisselkoers vast.
- Aandelen toont elke beursnotering één keer, met opgetelde aantallen en bedragen van alle brokers. Detailpagina’s openen altijd met alle brokertransacties.
- Sectoren, landen en beleggingstypen krijgen visuele verdelingen op basis van open beursnoteringen. Bedrijfslinks passen bij de huisstijl, met beurs en ticker onder de naam.
- De algemene brokerselector en dubbele kop verdwijnen op het aandelenoverzicht; de transactietabel onderaan is verwijderd. Aankopen toevoegen blijft beschikbaar via de pop-up.

## 0.20.0
- Dividendpagina toont alleen de eigen dashboardkop; algemene paginakop, brokerselector en koersstatus verdwijnen daar volledig.
- Home krijgt de optie Alle valuta’s in euro, met kerncijfers, totaalgrafiek, wegingen en posities in één overzicht.
- Aankoopinleg, verkopen en dividend worden op hun transactiedatum omgerekend; actuele marktwaarde tegen beschikbare actuele wisselkoersen. Britse pence worden correct verwerkt.
- Ontbrekende omrekeningen worden expliciet apart gehouden en historische wisselkoersen zo nodig opgehaald. Oorspronkelijke boekingen blijven intact.

## 0.19.0
- Nieuw dividenddashboard met kerncijfers per valuta, maandgrafiek, jaaroverzicht, kalender en grootste uitbetalers.
- Vooruitblik van 12 maanden, 3 jaar of 5 jaar op basis van de laatste twaalf maanden en huidige aantallen, met bekende splitsingen verwerkt.
- Verwachtingen zijn zichtbaar gescheiden van ontvangen betalingen, met uitleg over aannames en posities zonder bruikbare basis.
- Betalingen blijven filterbaar en sorteerbaar; dividend boeken blijft in een pop-up en grote overzichten laden betalingen in stappen.

## 0.18.0
- Dividend toont het cumulatieve percentage van de totale aankoopinleg sinds de eerste aankoop; groter bedrijfslogo.
- Bekende winst blijft zichtbaar bij ontbrekende koersen. Home noemt de betrokken aandelen direct, inclusief diagnostische Log-ID.
- Handmatige laatste koers per beursnotering (ook nul), met uitschakelen van automatische koers- en historieaanvragen en mogelijkheid tot hervatten.
- Databaseversie 15 bewaart laatste koersen, inclusief veilige migratie, back-up en herstel.

## 0.17.0
- Aandeelpagina met overzichtsblokken voor aantal, waarde in noteringsvaluta, eurowaarde en ontvangen dividend.
- Bedrijfslogo en korte bedrijfsomschrijving uit een bewaard bedrijfsprofiel, met rustige terugval als informatie ontbreekt.
- Teruglink en technische categorietoelichtingen verwijderd; eurowaarde gebruikt uitsluitend opgeslagen wisselkoersen van uiterlijk de koersdatum.

- Aandelencategorieën worden tijdens het aanvullen direct uit de opgeslagen metadata ververst, los van het gecachete portefeuilleoverzicht. Bij grote portefeuilles hoeft de lijst niet meer te wachten op de volledige koersronde.
- De aandelenpagina toont voortgang en onderscheidt nog ophalen, ophalen mislukt, ontbrekende brongegevens, handmatig leeggemaakte velden en de zelf te kiezen eigen categorie.
- Succesvolle aanvullingen maken de overzichtcache per aandeel ongeldig. De kleine metadata-aanvraag gebruikt geen koersdienst, herberekent geen historie en behoudt actieve kolomfilters en sortering.

## 0.16.1

- Profielaanvragen gebruiken het juiste antwoordformaat: HTML voor profielpagina’s en sessieopbouw, tekst voor de sessiecode en JSON voor de profiel-API. De aanvragen gebruiken ook een expliciete taalvoorkeur.
- HTTP 406 bij de directe profielaanvraag schakelt nu over naar de ingesloten API-respons op de profielpagina. Aanvraaglimieten (HTTP 429) blijven gerespecteerd.
- Foutlogs vermelden de precieze aanvraagstap, host, gevraagd formaat, HTTP-status en duur, zonder sessiegegevens of volledige antwoorden. Aanhoudende HTTP 406-fouten krijgen een gedeelde wachttijd om aanvraagpieken te voorkomen.

## 0.16.0

- Sector, land en type belegging worden eenmalig automatisch aangevuld via Yahoo Finance, ook voor bestaande aandelen. Profielen worden per ticker, beurs en valuta gecontroleerd en blijvend opgeslagen.
- Handmatige correcties winnen per veld, inclusief bewust leeg gemaakte velden. Bestaande categorieën uit 0.15.0 blijven behouden; de eigen categorie blijft handmatig.
- De detailpagina toont de API-status, ophaaldatum en ontbrekende gegevens. Verbindingsproblemen krijgen veilige diagnostische logs en een wachttijd voor opnieuw proberen; succesvolle profielen worden niet telkens opnieuw opgevraagd.
- Databaseversie 14 bewaart de voortgang en bescherming van handmatige categorieën, inclusief migratie, back-up en herstel.

## 0.15.0

- Open een aandeel vanuit de aandelenlijst voor een eigen detailpagina met koersgrafiek, periodekeuze en alle gekoppelde aankopen, verkopen, dividenden, splitsingen en kapitaalterugbetalingen. Gekoppelde openstaande importregels zijn herkenbaar als Te beoordelen.
- Sector, land, type belegging en een eigen categorie worden blijvend per beursnotering opgeslagen. Admins wijzigen deze in een pop-up; de indeling staat ook in de aandelenlijst en blijft behouden in back-ups.
- Klik op kolomkoppen om oplopend of aflopend te sorteren, ook in combinatie met kolomfilters. Home en Transacties sorteren en filteren vóór paginering.
- Databaseversie 13 voegt categorieën toe met automatische migratie en veiligheidsback-up; bestaande transacties en historie blijven behouden.

## 0.14.0

- Alle tabellen hebben combineerbare filters per kolom. Bij Home filteren deze vóór paginering; andere tabellen doorzoeken de geladen regels.
- Aantallen worden zonder wetenschappelijke nulnotatie getoond, met behoud van fractionele aandelen.
- Importlogs bevatten aantallen bronregels, aankopen, verkopen, duplicaten en te beoordelen regels. Afgewezen verkopen en splitsingen vermelden bezit, gevraagd aantal en verschil waar relevant.
- Bestaande transacties worden niet automatisch gewijzigd; ontbrekende historie en afgewezen regels blijven zichtbaar bij Te beoordelen.

# 0.13.1

- Foutieve importregels zonder geldige prijs of valuta worden niet meer aangeboden voor automatische beurskoppeling. De misleidende algemene TMX-aanvraagfout vervalt.
- AREB krijgt een exacte broker/ISIN-koppeling; historische TMX- en EPIX-transacties kunnen ook zonder actuele beursnotering gekoppeld worden. Deze koppelingen leveren geen fictieve koers op.
- Stock distribution en Custom stock distribution worden herkend als aandelenuitkering/omzetting en duurzaam apart gehouden voor controle van de over te dragen kostprijs. Automatisch boeken van fusies en CVR-rechten is nog niet ondersteund.
- Opgeslagen API-importvoorbeelden worden bij opnieuw openen bijgewerkt vanuit hun oorspronkelijke rapportregels, met behoud van bron-ID's en eerdere handmatige keuzes.
- GitHub publiceert na geslaagde controles automatisch de ontbrekende release voor de huidige appversie, met gevalideerde versie en changelogtekst. Commit, push en release zijn voortaan vaste projectafspraken.
- Lokale agentafspraken worden buiten de GitHub-repository gehouden.
- Databaseschema blijft 12.

# 0.13.0

- Home toont direct het portefeuilleoverzicht; de algemene paginakop, brokerselector en koersstatusbalk zijn daar verborgen. Het mobiele menu blijft bereikbaar.
- Transacties en aandelen aanpassen gebeurt in een modale pop-up, inclusief wijzigingshistorie en bestaande controles.
- Dezelfde pop-upstijl geldt voor aandelenkoppelingen, importbeoordelingen, gebruikers, dashboardinstellingen, API-verbindingen, nieuwe boekingen, brokeraccounts, beveiliging, herstellen en verwijderen.
- Pop-ups ondersteunen Sluiten/Annuleren, Escape en toetsenbordfocus; bij navigatie of afmelden sluiten ze.
- Vaste projectafspraak toegevoegd: toekomstige bewerkformulieren openen altijd in een pop-up.
- Appversie 0.13.0; databaseschema blijft 12.

# 0.12.0

- Nieuwe pagina Transacties: aankopen, verkopen, dividend, kapitaalterugbetalingen en splitsingen bekijken, zoeken en filteren per type/brokeraccount, met 50 regels per pagina.
- Admins kunnen datum, tijd, aantal, aankoop/verkooptype, prijs, ontvangen bedrag en dividendnotitie wijzigen waar van toepassing. De app controleert de volledige positiehistorie en weigert ongeldige verkopen of splitsingen.
- Originele importregels en bron-ID’s blijven behouden; correcties krijgen een blijvende wijzigingshistorie. Gelijktijdige wijzigingen worden niet overschreven.
- Instellingen biedt verwijderen van alle portefeuillegegevens of de administratie van één brokeraccount, inclusief bijbehorende imports en koppelingen. Vooraf verschijnt een overzicht en is de bevestiging VERWIJDEREN nodig.
- Vóór verwijderen wordt een volledige herstelback-up buiten de gewone back-uprotatie opgeslagen, met een downloadlink. Andere brokeraccounts, gebruikers, instellingen en API-verbindingen blijven behouden bij een gerichte verwijdering. Herimport van gewiste gegevens is mogelijk.
- Schema 12 voegt transaction_edits toe. Migratie en back-upherstel behouden de bestaande administratie; oudere back-ups blijven ondersteund.
- Het app-changelog (portfolio/CHANGELOG.md) is aangevuld met 0.11.0 en 0.12.0; voortaan worden het repository- en app-changelog bij iedere release samen bijgewerkt.

# 0.11.0

- Trading 212 herkent Return of capital manufactured payment automatisch als kapitaalterugbetaling. De ontvangst blijft in de bronvaluta en telt niet als dividendwinst.
- Stock split open past het volledige aantal aandelen aan met behoud van totale kostprijs, inleg en gerealiseerde winst. Stock split close controleert het oude aantal wanneer beide regels in hetzelfde bestand staan. Splitsingen zonder voorafgaand bezit blijven ter beoordeling staan.
- Bestaande afgewezen regels kunnen opnieuw worden geprobeerd; bronregels, eerdere handmatige keuzes en deduplicatie blijven behouden.
- Schema 11 voegt splitsingsmetadata toe. Migratie maakt vooraf een back-up; herstel ondersteunt oude en nieuwe back-ups.
- Versiegeschiedenis verplaatst uit README naar dit bestand. Voeg toekomstige wijzigingen hier bovenaan toe.

# 0.10.0

- Vernieuwd Home-dashboard met kerncijfers per valuta, grootste posities en beste/zwakste resultaten.
- Portefeuilletotaal als standaardgrafiek; gerichte vergelijking van maximaal zes posities.
- Lokaal doorzoekbare en sorteerbare positielijst met filters, wegingen en 25 regels per pagina.
- Responsieve grafiek zonder grote lege zijruimte, interactieve legenda en toetsenbordbediening.
- Dagwaardetabel pas opbouwen bij uitklappen, per 250 regels; geen extra providerverkeer voor dashboardfilters.
- Geen schemawijziging; schema blijft 10.

# 0.9.0

- Geldige importregels verwerken terwijl fouten duurzaam apart worden gehouden voor beoordeling.
- Admin-subpagina Te beoordelen met classificatie, opnieuw proberen en bewust overslaan; brondata en keuzes bewaren.
- Kapitaalterugbetalingen na expliciete keuze apart opslaan, zonder dividendwinst of automatische fiscale kostprijscorrectie.
- Savepoints per regel, idempotent opnieuw proberen en bescherming van eerder geboekte regels in gedeeltelijke imports.
- Madrid/OTC en gecontroleerde ISIN-koppelingen voor SAB, UNI en TCEHY.
- Schema 10 met automatische migratie-back-up en gevalideerd herstel van beoordelingen en kapitaalterugbetalingen.

# 0.8.0

- Admin-subpagina onder Imports voor blijvend opgeslagen en openstaande aandelenkoppelingen.
- Per brokeraccount, ISIN/bronticker en bronvaluta; bekende noteringen zonder nieuwe zoekaanvraag hergebruiken.
- Koersticker, beurs en valuta corrigeren met providercontrole; openstaande en volgende imports gebruiken de correctie, eerdere boekingen blijven behouden.
- Bestaande previewkoppelingen lokaal overnemen; register opnemen in back-up/herstel.
- Yahoo-aanvraaglimieten (429/503) laten koppelen pauzeren in plaats van alle instrumenten blijven proberen.
- Schema 9 met automatische veiligheidsback-up en transactionele migratie.

# 0.7.3

- Dividendontvangsten zonder lokale voorafgaande aankoop apart importeren met expliciete melding over ontbrekende aankoophistorie.
- Geen fictieve aankoop of kostprijs; brokeraccount, brongegevens, valutaomrekening en deduplicatie blijven behouden.
- Aantal van deze ontvangsten tonen na import. Schema blijft 8.

# 0.7.2

- Euronext Brussel en automatische ISIN-koppelingen voor Altria/MO en Sofina/SOF.
- Zoekcache vernieuwd voor nieuwe beursondersteuning; concrete koppelfouten ook naast de opslagknop.
- UTF-8-codering hersteld voor importmeldingen; expliciete charset voor JavaScript. Schema blijft 8.

# 0.7.1

- Importknop blijft na automatische koppeling bedienbaar; fouten per bronregel en ontbrekende koppelingen staan direct bij de knop.
- Bevestiging, voortgang en fouten bij opslaan worden naast de importknop getoond. Ongeldige batches blijven veilig geblokkeerd.
- Schema blijft 8.

# 0.7.0

- Nieuwe pagina Valuta met beschikbaar valutaoverzicht, historische rekenmachine en opgeslagen koershistorie.
- Frankfurter dagreferentiekoersen blijvend opslaan; 6-uurlijkse controle en historische import per jaar.
- Correcte GBX/GBp-eenheid (pence), London/Swiss-beurzen en issuer-gebaseerde ISIN-hints voor VWCE, VUSA, VFEA en EQGB.
- Historische prijs- en dividendomrekening naar de gecontroleerde noteringsvaluta; brondata en omrekenregistratie behouden.
- Geen half geboekte import bij ontbrekende koersen; Decimal-berekeningen en expliciete koersdatums.
- Schema 8 met valutametadata, koersen, dekking en importomrekeningen; migratieback-up en gevalideerd herstel.

# 0.6.0

- Automatische importkoppeling via ISIN, ticker en gecontroleerde koersvaluta; geen keuze per aandeel meer.
- Broker-tickers normaliseren, ETF's meenemen en extra beurscodes ondersteunen.
- Koppelingen bewaren in SQLite en hergebruiken; onzekere resultaten en valuta-afwijkingen niet gokken.
- Opgeslagen importvoorbeelden opnieuw openen en automatisch laten koppelen.
- Nieuwe resolver- en open-endpoints alleen voor admins; bevestiging van volledige import blijft verplicht.
- Schema blijft 7; bestaande previews en API-verbindingen blijven behouden.

# 0.5.4

- Trading 212 CSV en API ondersteunen de datumkolom Time (UTC), naast Time.
- Reeds opgeslagen deelrapporten na deze fout lokaal hervatten zonder nieuwe API-aanvraag.
- Deelrapporten met verschillende datum- en aanvullende belastingkolommen combineren.
- Dubbele kolomnamen en tegenstrijdige tijdvelden blokkeren in plaats van gegevens te gokken.
- Bron-ID's en deduplicatie behouden bij de gebruikelijke tijdnotatie; schema blijft 7.

# 0.5.3

- Concrete lokale foutreden in de logmelding en details, in plaats van alleen ValueError.
- Herkenbare codes voor lopende/ontbrekende aanvragen, wachttijden, geweigerde downloadhosts en CSV-kolommen.
- Context met importstap, omgeving, rapportnummer, periode, voortgang en resterende wachttijd.
- Alleen expliciet veilige appmeldingen loggen; onbekende externe foutteksten blijven afgeschermd.
- Schema blijft 7; API-verbindingen en lopende meerjarige importplannen blijven behouden.

# 0.5.2

- Oplossing voor Trading 212 HTTP 400: rapportperioden mogen maximaal één jaar beslaan.
- Lange perioden automatisch opsplitsen in delen van maximaal 364 dagen, ook rond schrikkeljaren.
- Delen via statuscontrole na elkaar aanvragen en samenvoegen tot één volledig importvoorbeeld.
- Voortgang en opgehaalde rapporten blijven behouden na fouten en herstarten.
- Lege rapportperioden afhandelen zonder onnodige boekingen; bestaande bron-ID-deduplicatie blijft actief.
- Begindatum standaard 1 januari van het huidige jaar; kies voor volledige historie je eerste transactie.
- Schema blijft 7; geen databasemigratie of nieuwe API-sleutels nodig.

# 0.5.1

- Nieuwe pagina Logs voor ingelogde admins; servercontrole op bekijken en downloaden.
- Gedeelde loggingmodule, opgeslagen in SQLite met maximaal 7 dagen en 5.000 regels.
- Trading 212-fouten met HTTP-status en Log-ID; providerfout, periode, omgeving en requestdetails afgeschermd terugvinden.
- Zoeken op Log-ID/melding, filters, paginering en JSON-download van de getoonde pagina.
- Centrale filtering van credentials, geheime velden, autorisatie, e-mailadressen en URL's.
- Ook logging voor marktdatafouten, achtergrondtaken en afgewezen app-aanvragen.
- Schema 7 voegt de logtabel toe; transactionele migratie met veiligheidsback-up.

# 0.5.0

- Trading 212 API-verbinding per brokeraccount, voor Live en Demo.
- Rapport aanvragen, later ophalen en controleren via dezelfde importpreview als CSV.
- Alleen admin met ingeschakelde gebruikersbeveiliging; CSRF op iedere actie.
- Sleutels versleuteld buiten SQLite, lokale encryptiesleutel en beperkte bestandsrechten.
- Rapportstatus en downloads in SQLite-cache, aanvraagbegrenzing en taakbehoud na herstart.
- Credentials nooit naar downloadhosts; vaste API-hosts, HTTPS-downloadcontrole en geen redirects.
- API- en CSV-imports delen bron-ID-controle; bestaande importbeperkingen blijven gelden.
- Database blijft schema 6; geen migratie nodig. Nieuwe cryptography-afhankelijkheid.

# 0.4.0

- Blijvende API-cache in SQLite, zoekdata een week en versiecontrole een dag gecachet.
- Historie incrementeel aanvullen; beurskoersen delen tussen brokeraccounts.
- Meerdere brokeraccounts, rekeningfilter en accountkoppeling bij transacties/dividend.
- Nieuwe uitbreidbare importmodule met Trading 212 History CSV-adapter.
- Preview, expliciete beurskoppeling, transactiecontrole en deduplicatie per rekening.
- Geïmporteerde verkopen verwerken met gemiddelde kostprijs en gerealiseerde winst.
- Versiecontrole onder Instellingen; installeren blijft via Home Assistant lopen.
- Schema 6; bestaande invoer blijft behouden onder Handmatig. Back-ups bevatten ook accounts, importregister en API-cache.

# 0.3.1

- Gebruikershoek linksonder in het zijmenu; accountbediening rechtsboven verwijderd.
- Account aanpassen met eigen gebruikersnaam en optioneel nieuw wachtwoord.
- Huidig wachtwoord verplicht, rol blijft behouden en na wijziging opnieuw aanmelden.
- Inlogknop in de gebruikershoek wanneer je bent uitgelogd.

# 0.3.0

- Back-up downloaden alleen onder Instellingen; gevalideerd terugzetten met veiligheidskopie vooraf.
- Gebruikersbeveiliging inschakelbaar onder Instellingen; eigen eerste admin, geen standaardwachtwoorden.
- Admin- en basicrollen, servercontrole, gebruikersbeheer, accountdeactivering en wachtwoordwijziging.
- PBKDF2-wachtwoordhashes, HttpOnly-sessies, sessieverloop, CSRF-controle en inlogbegrenzing.
- Herstel behoudt huidige accounts en rollen en meldt actieve sessies af.
- Servercache, ETags, versiegebonden assetcache en hergebruik van recente koersen.
- Schema 5 voegt accounts en de beveiligingsoptie toe; bestaande gegevens blijven behouden.

# 0.2.1

- De app heet overal Home Invest: app store, HA-zijbalk, menu, browsertitels en documentatie.

# 0.2.0

- Linkerzijbalk met Home, Aandelen, Dividend, Rapporten en Instellingen.
- Afzonderlijke paginaweergaven met directe links en ondersteuning voor terug/herladen.
- Inklapbaar menu op kleine schermen.
- Maandrapport voor dividend met jaarfilter en actuele portefeuilletotalen.
- Standaard grafiekperiode blijvend instelbaar.
- Geversioneerde databasemigraties met back-up vooraf en transactionele rollback.
- Schema 4 voegt dashboardinstellingen toe; bestaande schema's 1, 2 en 3 worden automatisch bijgewerkt.

# 0.1.3

- Alle aandelen samen zichtbaar met een eigen procentuele winstlijn per aandeel.
- Portefeuilletotalen per valuta in de grafiek, met aparte lijn inclusief dividend.
- Ontvangen netto dividend apart boeken met betaaldatum en notitie.
- Eigen dividendregister en SQLite-tabel, meegenomen in back-ups.
- Koerswinst, dividend en totale winst afzonderlijk zichtbaar, ook in daghistorie.

# 0.1.2

- Historische dagkoersen vanaf de aankoopdatum automatisch ophalen en opslaan.
- Elke kalenderdag zichtbaar, met laatst bekende koers op dagen zonder handel.
- Zoomknoppen 1W, 1M, 3M, 6M, YTD, 1Y en Alles.
- Grafiekassen, aanwijzen van dagwaardes en uitklapbare dagtabel.
- Bestaande databases worden uitgebreid met behoud van aankopen en back-ups.

# 0.1.1

- Zoek aandelen op naam of symbool vanaf twee tekens.
- Kies een resultaat om naam, symbool, beurs en valuta automatisch in te vullen.
- Ondersteunt Amsterdam, Nasdaq en NYSE; dubbele noteringen blijven herkenbaar.
- Korte zoekvertraging en cache beperken aanvragen; oude zoekresultaten worden genegeerd.

# 0.1.0

- Eerste experimentele versie met HA ingress-dashboard.
- Handmatige aankopen, SQLite, Yahoo-koersen en grafiek per aandeel.
- Gescheiden totalen per valuta, dagelijkse back-ups en download.

