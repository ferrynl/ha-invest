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

# Changelog

## 0.13.1 — 22 oktober 2026

- Foutieve importregels zonder geldige prijs of valuta worden niet meer aangeboden voor automatische beurskoppeling. De misleidende algemene TMX-aanvraagfout vervalt.
- AREB krijgt een exacte broker/ISIN-koppeling; historische TMX- en EPIX-transacties kunnen ook zonder actuele beursnotering gekoppeld worden. Deze koppelingen leveren geen fictieve koers op.
- Stock distribution en Custom stock distribution worden herkend als aandelenuitkering/omzetting en duurzaam apart gehouden voor controle van de over te dragen kostprijs. Automatisch boeken van fusies en CVR-rechten is nog niet ondersteund.
- Opgeslagen API-importvoorbeelden worden bij opnieuw openen bijgewerkt vanuit hun oorspronkelijke rapportregels, met behoud van bron-ID's en eerdere handmatige keuzes.
- GitHub publiceert na geslaagde controles automatisch de ontbrekende release voor de huidige appversie, met gevalideerde versie en changelogtekst. Commit, push en release zijn voortaan vaste projectafspraken.
- Lokale agentafspraken worden buiten de GitHub-repository gehouden.
- Databaseschema blijft 12.

## 0.13.0 — 22 oktober 2026

- Home toont direct het portefeuilleoverzicht; de algemene paginakop, brokerselector en koersstatusbalk zijn daar verborgen. Het mobiele menu blijft bereikbaar.
- Transacties en aandelen aanpassen gebeurt in een modale pop-up, inclusief wijzigingshistorie en bestaande controles.
- Dezelfde pop-upstijl geldt voor aandelenkoppelingen, importbeoordelingen, gebruikers, dashboardinstellingen, API-verbindingen, nieuwe boekingen, brokeraccounts, beveiliging, herstellen en verwijderen.
- Pop-ups ondersteunen Sluiten/Annuleren, Escape en toetsenbordfocus; bij navigatie of afmelden sluiten ze.
- Vaste projectafspraak toegevoegd: toekomstige bewerkformulieren openen altijd in een pop-up.
- Appversie 0.13.0; databaseschema blijft 12.

## 0.12.0 — 22 oktober 2026

- Nieuwe pagina Transacties: aankopen, verkopen, dividend, kapitaalterugbetalingen en splitsingen bekijken, zoeken en filteren per type/brokeraccount, met 50 regels per pagina.
- Admins kunnen datum, tijd, aantal, aankoop/verkooptype, prijs, ontvangen bedrag en dividendnotitie wijzigen waar van toepassing. De app controleert de volledige positiehistorie en weigert ongeldige verkopen of splitsingen.
- Originele importregels en bron-ID’s blijven behouden; correcties krijgen een blijvende wijzigingshistorie. Gelijktijdige wijzigingen worden niet overschreven.
- Instellingen biedt verwijderen van alle portefeuillegegevens of de administratie van één brokeraccount, inclusief bijbehorende imports en koppelingen. Vooraf verschijnt een overzicht en is de bevestiging VERWIJDEREN nodig.
- Vóór verwijderen wordt een volledige herstelback-up buiten de gewone back-uprotatie opgeslagen, met een downloadlink. Andere brokeraccounts, gebruikers, instellingen en API-verbindingen blijven behouden bij een gerichte verwijdering. Herimport van gewiste gegevens is mogelijk.
- Schema 12 voegt transaction_edits toe. Migratie en back-upherstel behouden de bestaande administratie; oudere back-ups blijven ondersteund.
- Het app-changelog (portfolio/CHANGELOG.md) is aangevuld met 0.11.0 en 0.12.0; voortaan worden het repository- en app-changelog bij iedere release samen bijgewerkt.

## 0.11.0 — 22 oktober 2026

- Trading 212 herkent Return of capital manufactured payment automatisch als kapitaalterugbetaling. De ontvangst blijft in de bronvaluta en telt niet als dividendwinst.
- Stock split open past het volledige aantal aandelen aan met behoud van totale kostprijs, inleg en gerealiseerde winst. Stock split close controleert het oude aantal wanneer beide regels in hetzelfde bestand staan. Splitsingen zonder voorafgaand bezit blijven ter beoordeling staan.
- Bestaande afgewezen regels kunnen opnieuw worden geprobeerd; bronregels, eerdere handmatige keuzes en deduplicatie blijven behouden.
- Schema 11 voegt splitsingsmetadata toe. Migratie maakt vooraf een back-up; herstel ondersteunt oude en nieuwe back-ups.
- Versiegeschiedenis verplaatst uit README naar dit bestand. Voeg toekomstige wijzigingen hier bovenaan toe.

### Nieuw Home-overzicht (0.10.0)

Home opent met het portefeuilletotaal in EUR (of de eerste aanwezige valuta). Valutaknoppen houden bedragen gescheiden; de kerncijfers tonen marktwaarde, openstaande kostprijs, totale winst en dividend dat aan deze posities gekoppeld is. Ontbrekende koersen worden expliciet gemeld. Er wordt geen automatische EUR-conversie verondersteld.

Gebruik de positielijst om lokaal te zoeken op bedrijf, ticker, beurs of brokeraccount. Filter open/gesloten posities, ontbrekende koersen en positieve/negatieve resultaten; sorteer op waarde, weging, naam of winstpercentage. De lijst toont 25 regels per pagina. **Bekijken** opent de grafiek van die positie. Selecteer maximaal zes posities met de selectievakjes om ze gericht te vergelijken; de standaardgrafiek tekent niet meer alle honderd lijnen tegelijk.

Grootste posities toont de vijf grootste bekende marktwaarden binnen de gekozen valuta. Beste/zwakste resultaat toont winst sinds aankoop gedeeld door de totale oorspronkelijke inleg, inclusief gekoppeld dividend. Dit is geen tijdgewogen rendement en geen rendement over de geselecteerde grafiekperiode. Een periodeknop verandert alleen de getoonde datums.

De grafiek vult de beschikbare breedte en ondersteunt muis en pijltjestoetsen. Via de legenda kun je lijnen aan/uit zetten. Dagwaarden worden pas opgebouwd bij uitklappen, per 250 regels, zodat lange historie en veel posities de pagina niet met duizenden tabelregels belasten. Zoeken, sorteren en selectie gebruiken de reeds opgehaalde gegevens en doen geen extra koersaanvragen. Schema blijft 10; bestaande gegevens en back-ups blijven bruikbaar.
### Importeren met beoordeling achteraf (0.9.0)

Klik **Import definitief opslaan**, ook als sommige noteringen of bronregels nog niet kloppen. Geldige regels worden opgeslagen. Ontbrekende koppelingen, onbekende acties, ontbrekende wisselkoersen, ongeldige verkopen en bron-ID-conflicten komen duurzaam in **Imports > Te beoordelen**. Een import met uitsluitend fouten wordt ook gestart en levert een beoordelingslijst op. Het bestand moet wel een leesbare Trading 212 CSV zijn.

Per regel kies je **Opnieuw proberen**, **Kapitaalterugbetaling**, **Ontvangen dividend**, **Aankoop**, **Verkoop** of **Bewust overslaan**. Er wordt niets geschat: de gekozen classificatie gebruikt de oorspronkelijke bedragen en datum; ontbreken noodzakelijke waarden, dan blijft de regel apart staan. Herstel ontbrekende noteringen bij Aandelenkoppelingen en probeer de regels daarna opnieuw. Een keuze verwerkt ook andere inmiddels opgeloste regels in dezelfde import opnieuw. Reeds geboekte regels worden herkend en niet dubbel opgeslagen.

Kapitaalterugbetalingen (zoals Return of capital manufactured payment) worden pas na jouw keuze apart opgeslagen, in de bronvaluta. Ze staan onder Te beoordelen in een afzonderlijk overzicht en tellen niet als dividendwinst. Er wordt geen automatische fiscale kostprijscorrectie gedaan. De oorspronkelijke bronregel en keuze blijven bewaard. Bewust overslaan bewaart de bronregel eveneens; bestaande boekingen worden nooit overschreven.

De import is per regel transactioneel: een mislukte regel laat geen aankoop, dividend, omrekening of importregistratie achter. Andere geldige regels mogen wel slagen. Imports met resterende regels staan in de geschiedenis als **Deels verwerkt - beoordeling nodig**. De beheerpagina toont maximaal 2.000 beoordelingen (openstaande eerst) en 500 kapitaalterugbetalingen; alle gegevens blijven in SQLite bewaard. Alleen admins hebben toegang.

Schema 10 voegt de beoordelingslijst en kapitaalterugbetalingen toe, met automatische migratie-back-up, herstelvalidatie en ondersteuning voor oudere back-ups. Bestaande openstaande importvoorbeelden kunnen opnieuw worden gestart zonder nieuwe brokerexport.

Madrid en Amerikaanse OTC-noteringen worden nu ondersteund. De ISIN-koppelingen voor SAB (ES0113860A34), UNI (ES0180907000) en TCEHY (US88032Q1094) worden via actuele koersmetadata gecontroleerd.

Noteringsbronnen: [Banco Sabadell bij BME](https://www.bolsasymercados.es/en/bme-exchange/prices-and-markets/shares/detail.banco-de-sabadell-es0113860a34.html), [Unicaja ISIN](https://www.unicajabanco.com/content/dam/unicaja/unicaja-corporacion/documentos-corporacion/junta-general-de-accionistas/2021-extraordinaria/2021-extraordinaria-documento-conforme-reglamento-ue-en.pdf), [Tencent ADR bij Citi](https://depositaryreceipts.citi.com/adr/notices/pgm_dispCA.aspx?cusip=88032Q109&pageId=15&subpageID=112).

### Blijvende aandelenkoppelingen (0.8.0)

Open **Imports > Aandelenkoppelingen beheren** (alleen admin). De subpagina toont alle bekende en openstaande instrumenten uit eerdere importvoorbeelden, per brokeraccount, ISIN/bronticker en bronvaluta. De lijst en lokaal zoeken gebruiken geen koersdienst. Bekende koppelingen blijven in SQLite zonder vervaldatum bewaard, ook na herstart. Bestaande opgeslagen previewkoppelingen worden lokaal overgenomen.

Kies **Corrigeren** of **Koppelen**, vul de juiste Yahoo-koersticker in en klik **Notering controleren**. Beurs en noteringsvaluta worden opgehaald; **Koppeling opslaan** controleert dat ze bij die notering horen. Controleer zelf ook de identiteit/ISIN van het gekozen aandeel. Een foutieve beurs of valuta wordt niet opgeslagen. Een manuele correctie wordt niet overschreven door automatisch koppelen. Open je importvoorbeeld daarna opnieuw.

Correcties gelden voor openstaande en volgende imports. Eerder geboekte transacties, oorspronkelijke CSV-regels en de gebruikte omrekeningen blijven als administratie behouden; bestaande boekingen worden niet stilzwijgend van aandeel of valuta veranderd. Het register is geen functie om oude boekingen opnieuw te waarderen.

Dezelfde eenduidige ISIN-koppeling kan voor een andere bronvaluta worden hergebruikt; de historische omrekening blijft gelden. Bij een Yahoo 429/503 stopt het automatisch koppelen en geldt een opgeslagen wachttijd (Retry-After, minimaal 60 seconden). Reeds opgeslagen koppelingen blijven bruikbaar. Nieuwe instrumenten kunnen nog koersaanvragen nodig hebben.

Schema 9 voegt het koppelingenregister toe, met automatische migratie-back-up en ondersteuning in back-up/herstel. De regels met **Dividend (Return of capital manufactured payment)** blijven expliciet geblokkeerd: kapitaalterugbetaling is geen gewoon dividend en wordt niet stilzwijgend als winst geboekt. Dit is een apart probleem, geen API-limiet. Een oudere importperiode of beheer van beurskoppelingen lost dat transactietype niet op.

### Dividend zonder aankoophistorie (0.7.3)

Een gecontroleerde dividendontvangst kan worden geimporteerd als de voorafgaande aankoop niet in de gekozen periode of lokale historie staat. De ontvangst blijft bij het gekozen brokeraccount, met een melding bij Dividend en in het importresultaat. Er wordt geen aankoop, aantal of kostprijs aangemaakt. De ontvangst staat in Dividend en Rapporten; een totaalrendement op een positie vereist aankoophistorie. Automatische beurskoppeling, historische valutaomrekening, deduplicatie en volledige rollback blijven gelden. Bestaande voorbeelden kunnen opnieuw worden opgeslagen. Schema blijft 8.

### Automatische koppeling MO en SOF (0.7.2)

Euronext Brussel wordt nu ondersteund. Gecontroleerde ISIN-koppelingen voor Altria (US02209S1033, MO in USD) en Sofina (BE0003717312, SOF.BR in EUR) werken ook bij onvolledige zoekresultaten. Afwijkende bronvaluta wordt via de bestaande historische omrekening verwerkt. Open je bestaande importvoorbeeld en klik Automatisch opnieuw koppelen. Schema blijft 8.

Noteringsbronnen: [Altria NYSE MO](https://investor.altria.com/stock-performance/default.aspx), [Altria ISIN](https://live.euronext.com/nl/product/equities/US02209S1033-BGEM/market-information), [Sofina ISIN en Brussel](https://live.euronext.com/en/product/equities/BE0003717312-XBRU).

### Importknop (0.7.1)

Na de automatische koppeling is de opslagknop bedienbaar. Eventuele fouten per bronregel of ontbrekende koppelingen staan direct bij de knop. De bevestiging slaat deze controles niet over; corrigeer gemelde bronfouten voordat je opnieuw importeert. Fouten bij het opslaan verschijnen ook naast de knop. Schema blijft 8.

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
