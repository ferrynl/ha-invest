## 0.70.37

- Vertel op Over ons het verhaal achter Home Invest in het Nederlands, Engels en Spaans.

## 0.70.36

- Vermeld op Over ons dat Home Invest is ontwikkeld voor alle inwoners van de EU en voeg het Made in Europe-logo toe.

## 0.70.35

- Maak het Home Invest-logo beter leesbaar in lichte en donkere thema’s.
- Breid de appbeschrijving uit en voeg uitleg toe in het Nederlands, Engels en Spaans.

## 0.70.34

- Nieuw 3D-logo voor Home Invest op het welkomstscherm, in de app en in de appwinkel van Home Assistant.

## 0.70.33

- Voeg regressiecontroles toe voor de veilige Home Assistant-ingressconfiguratie en standaard niet-gepubliceerde sensorpoort.
- Documenteer veilige remote toegang via Home Assistant, VPN en reverse proxy.
- Verminder SQLite-schrijflocks bij sessiecontroles: valide sessies worden meestal gelezen en pas vlak voor verloop verlengd.
- Test dat sessiecontroles onder databasebelasting blijven werken en dat sessieverloop en accountintrekking geldig blijven.

## 0.70.32

- Handel tijdelijke SQLite-databaselocks bij transactieverzoeken veilig af met HTTP 503 en een duidelijke melding om eerst de transactiestatus te controleren.
- Voorkom automatisch opnieuw uitvoeren van financiële boekingen bij een bezette database.
- Voeg regressietest toe voor de verwerking van een vergrendelde database en vertaal de foutmeldingen naar Nederlands, Engels en Spaans.

## 0.70.31

- Voeg financiële datakwaliteitscontrole toe aan Health Center met signalering van ongeldige transacties, zonder transacties automatisch te wijzigen.
- Controleer mogelijke dubbele transacties, brokerisolatie en nauwkeurigheid van aantallen met aanvullende regressietests.
- Voorkom dat een opslag-time-out ten onrechte uitnodigt tot opnieuw boeken: adviseer eerst de transactiegeschiedenis te controleren.
- Werk browsertests, vertalingen (Nederlands, Engels en Spaans) en testdekking bij.
- Verminder onnodige dubbele testuitvoeringen in de Revolut-exporttest.

## 0.70.30

- Versnel de koersverversing door aankoopdatums en omboekingsverkopen eenmalig te indexeren in plaats van voor elke positie opnieuw transacties te doorlopen.
- Sla posities zonder bruikbare aankoopdatum veilig over zonder de volledige koersverversing te onderbreken.
- Voeg regressietests toe voor omboekingen, meerdere valuta's en grote aantallen transacties.
- Voorkom dubbele GitHub Actions-controles bij branch-pushes en pull requests en annuleer achterhaalde checks automatisch.
- Gebruik één hoofdchangelog met een gecontroleerde, gesynchroniseerde kopie voor de Home Assistant-add-on.
- Behoud de afzonderlijke CodeQL-beveiligingsscan en de bestaande release-, browser-, Docker- en beveiligingscontroles.

## 0.70.29

- Geef Health Center een herkenbaar hartslagicoon in het hoofdmenu.
- Toon op mobiel een compact controleoverzicht met één duidelijke samenvatting en status per controle.
- Maak herstelknoppen kleiner en groepeer technische en financiële controles met uitklapbare details.
- Voeg browsercontroles toe voor de mobiele Health Center-weergave.

## 0.70.28

- Voeg het Health Center toe met database-, opslag-, back-up- en beveiligingscontroles.
- Signaleer ontbrekende koersen, mogelijke dubbele transacties en andere financiële afwijkingen.
- Voeg veilige acties toe voor koersverversing en dashboardcache.
- Versterk containerbeveiliging en automatische upgrade- en browsertests.

## 0.70.27

- Controleer back-ups vooraf en bied versleutelde back-updownloads.
- Vraag het Home Invest-wachtwoord opnieuw bij gevoelige acties.
- Toon verouderde koersen en wisselkoersen en geef na import toegang tot controles.

## 0.70.26

- Beperk sessies tot 30 minuten inactiviteit en maximaal 12 uur. Meld na de upgrade opnieuw aan.
- Controleer toegangsrechten voor het inlezen van uploads en begrens de uploadduur en gelijktijdige verbindingen.

## 0.70.25

- Zoek automatisch naar mogelijke noteringen als de exacte controle van een importkoppeling mislukt.

## 0.70.24

- Voeg de geverifieerde CIBEY-notering toe voor Trading 212 en toon een begrijpelijke melding bij een onverwacht antwoord tijdens noteringcontrole.

## 0.70.23

- Toon mogelijke beurzen bij ontbrekende importkoppelingen, met een expliciete melding als de beurs onbekend is.

## 0.70.22

- Laat transactiewijzigingen opslaan tijdens een lopende koersverversing. Databasewijzigingen blijven geserialiseerd.

## 0.70.21

- Vernieuw de portefeuille en transactielijst op de achtergrond na het opslaan van een correctie. Begrens de wachttijd op het opslagantwoord.

## 0.70.20

- Corrigeer het ontvangen aantal van een omboeking vanuit Transacties, met veiligheidsback-up en controle op latere verkopen.

## 0.70.19

- Toon de meegenomen kostprijs van bestaande omboekingen in Transacties en op de aandeeldetailpagina.

## 0.70.18

- Zoek alle Amsterdamse noteringen op ticker zonder .AS, ook als ze nog niet in de portefeuille staan.

## 0.70.17

- Behoud brokeraccount en transactiedatum na het opslaan van een transactie.

## 0.70.16

- Zoek NN Group met NN of NN.AS. Opgeslagen noteringen zijn ook vindbaar zonder beursachtervoegsel.

## 0.70.15

- Ondersteun noteringen op Euronext Dublin in euro met Yahoo-tickers die eindigen op .IR.

## 0.70.14

- Toon opgeslagen noteringen bovenaan bij zoeken op exacte ticker, ook als Yahoo niet bereikbaar is.

## 0.70.13

- Resultaten in beeld toont bij 1D de koersbeweging van de laatste beschikbare sessie en opent die sessie op de aandeeldetailpagina.

## 0.70.12

- Toon bij een enkele grafiekdag een punt en geef de klikbare resultaten een groene aanwijskleur.

## 0.70.11

- Open aandeeldetails direct vanuit Resultaten in beeld op Home.

## 0.70.10

- Home, Stijgers en dalers en Aandeeldetails gebruiken dezelfde lokale bedrijfslogo-opslag als Dividend. De bronvermelding staat in de voettekst.

## 0.70.9

- Over ons herstelt het kaart­raster. Alleen de logobalk vult de kaartbreedte en toont een bronnaam als er geen afbeelding beschikbaar is.

## 0.70.8

- Over ons laadt logo’s ook wanneer de logorij nog verborgen is. De lokale logo-opslag volgt doorverwijzingen binnen dezelfde CDN-host en registreert download-, afbeeldings- en opslagfouten.

## 0.70.7

- Over ons toont grotere logo’s in kaarten over de volle breedte. Bronlogo’s en dividendlogo’s worden apart lokaal bewaard na de eerste download.

## 0.70.6

- Over ons toont logo’s bij bedrijven en databronnen en vermeldt AllInvestView als bron voor de dividendlogo’s.

## 0.70.5

- De dividendkalender haalt bedrijfslogo’s op via Ticker Logos zonder API-sleutel, met vaste bronverwijzingen voor VanEck, iShares, Alphabet en Banco Sabadell.

## 0.70.4

- Het dividendoverzicht leest posities en historie in dezelfde database-snapshot, zodat gelijktijdige koersupdates het laden niet meer afbreken.

## 0.70.3

- De dividendkalender gebruikt lokale bedrijfslogo’s en optioneel Logo.dev. Bij een ontbrekend logo blijft de ticker zichtbaar.

## 0.70.2

- Bedrijfslogo’s in de dividendkalender krijgen lichte tegels met meer ruimte. Bij een te klein logo blijft de ticker zichtbaar.

## 0.70.1

- Dividend probeert het overzicht opnieuw op te bouwen als een koersupdate de portefeuille tegelijk wijzigt. Serverfouten krijgen een logreferentie en de browser onderscheidt laad- en weergavefouten.

## 0.70.0

- Dividendkolommen openen alle geboekte betalingen van de gekozen maand. De dividendkalender toont bedrijfslogo’s en opent per maand de geschatte bedragen per bedrijf en brokeraccount.

## 0.69.2

- Dividend blijft laden bij posities met ontbrekende aantallen of onbruikbare koershistorie. Geboekte dividendbetalingen blijven zichtbaar.

## 0.69.1

- Home herstelt het euro-overzicht bij gelijktijdige koersupdates. Als het gecombineerde overzicht tijdelijk niet laadt, blijven posities in EUR zichtbaar met een toelichting.

## 0.69.0

- Aandelen heeft een subpagina Stijgers en dalers met een brokerkeuze en ranglijsten voor de laatste handelsdag of de afgelopen 7, 30, 90 of 365 dagen.

## 0.68.2

- Home laadt bedrijfsiconen ook als de bedrijfsinformatie nog niet is opgeslagen. Links hebben appbreed een witte standaardkleur en de ranglijsten gebruiken neutrale scheidingslijnen.

## 0.68.1

- Home toont de cijfers van gisteren met datum wanneer de lijst met stijgers of dalers van vandaag leeg is.

## 0.68.0

- Home toont de top vijf stijgers en dalers van vandaag binnen je broker- en valutaselectie, met logo, naam, beurs en procentueel koersverschil.

## 0.67.0

- Open vanaf Aandelen een sectorpagina met posities, landen en algemene sectorinformatie. Vergelijk de koersontwikkeling van je huidige selectie in EUR met een sector-ETF.

## 0.66.0

- De Home-grafiek blijft werken als een positie ongeldige koershistorie heeft. Bij gewijzigde gegevens probeert de app opnieuw en bij een fout toont hij de oorzaak en een beschikbaar Log-ID.

## 0.65.0

- Dashboard aanpassen biedt grafiek- en kaartvoorbeelden, verwisselbare cijfers, eigen titels en stijlen, en extra cijferkaarten.

## 0.64.0

- Home heeft tien grafiekkeuzes en een persoonlijke standaardgrafiek onder Instellingen → Dashboard. De grafiek verwerkt de gekozen periode en laadt eurohistorie pas wanneer ze bijna in beeld komt.

## 0.63.0

- Beheer ontbrekende koersen, contante afwikkelingen en de TMX-omboeking op één pagina. Een volledig afgewikkelde notering stopt automatisch met koersaanvragen en blijft in de historie.

## 0.62.0

- Het rendementsoverzicht rekent verder met bruikbare gegevens bij ontbrekende koersen, omrekeningen of ongeldige regels. Onder elk rapport staan de toelichting en de gevonden problemen per regel.

## 0.61.0

- Het inlogscherm krijgt een beursachtergrond met koerslijnen en candlesticks.

## 0.60.0

- Het inlogscherm krijgt een 3D-uitstraling, aparte keuzes voor wachtwoord en passkey, en een zichtbare melding over lokale opslag.

## 0.59.0

- Home opent met alle valuta’s geselecteerd en toont de marktwaarde per valuta in een eigen kleur, omgerekend naar euro.

## 0.58.0

- Log via HTTPS in bij Home Invest met een passkey, bijvoorbeeld via Windows Hello, je vingerafdruk of de schermvergrendeling van je telefoon.
- Voeg passkeys toe of verwijder ze via je accountinstellingen met bevestiging van je huidige wachtwoord. Inloggen met je wachtwoord blijft beschikbaar.
- Als de Home Assistant-app geen passkeys ondersteunt, open Home Invest via HTTPS in een gewone browser.

## 0.57.0

- Back-ups en updates toont alle lokale back-up- en updatebestanden, inclusief migratie- en veiligheidskopieën in submappen, met datum, grootte en totaalgebruik.
- Opgeslagen bestanden kunnen worden gedownload of na bevestiging verwijderd. SQLite-back-ups kunnen rechtstreeks worden hersteld, ook boven de uploadlimiet van 25 MB, met behoud van gebruikers en beveiliging.
- Herstellen maakt vooraf een veiligheidskopie; bestandsacties vereisen adminrechten, sessiebeveiliging en een ongewijzigd bestand.
- Statistieken verwijst naar bestandsbeheer; op mobiel worden bestanden als leesbare kaarten weergegeven.

## 0.56.0

- Dividend: instelbare jaarlijkse dividendgroei, standaard 3%, samengesteld vanaf volgend kalenderjaar.
- Verwachtingen duidelijk onderscheiden van niet-beschikbare aangekondigde uitkeringen.
- Toekomstige jaarvergelijking toont volledige kalenderjaren.

## 0.55.0 · 2 november 2026

- Instellingen > Gegevens opschonen biedt een gecontroleerd overzicht, volledige veiligheidskopie, verwijdering van tijdelijke/verlopen caches en overtollige koerswaarnemingen en het verkleinen van de database. Boekingen, dagelijkse koershistorie en ETF-samenstellingen blijven behouden. Bij back-upopschoning blijven de vijf nieuwste app-back-ups staan; dit beleid geldt ook voor volgende automatische app-back-ups.

- Een bestaande aankoop met jaartal 0026 kon bijna tweeduizend jaar dagwaarden veroorzaken. De grafiek bouwt voor transacties vóór 1900 alleen een bereik vanaf betrouwbare recente transacties/koersdatums op. De oorspronkelijke transacties, aantallen en kostprijs blijven behouden; de oude datum wordt nooit automatisch naar een andere eeuw gewijzigd.
- Home waarschuwt voor deze datums. Statistieken toont de afwijkende datums en aantallen met een link naar de betrokken transacties, die een admin via de bestaande bewerkpopup kan controleren.
- Nieuwe boekingen, transactiecorrecties en importboekingen weigeren datums vóór 1900 met een duidelijke jaartalcontrole.

## 0.54.0 · 2 november 2026

- Compacte overzichten laden koersgegevens per positie en nemen de volledige lijst ruwe koerswaarnemingen niet meer mee in de cache. Per kalenderdag wordt alleen de laatste waarneming verwerkt; de oorspronkelijke koersgegevens blijven bewaard.
- Dividend en rendement gebruiken alleen hun benodigde historische datums, zodat deze pagina’s geen volledige portefeuillehistorie meer in het geheugen opbouwen.
- Statistieken bevat diagnostiek met piekgeheugen, anoniem/bestands-/wisselgeheugen waar beschikbaar, lopende berekeningen, cache-afwijzingen en berekeningstijden, aantallen posities en de oudste historiedatums. Admins kunnen een technisch diagnosebestand downloaden zonder posities, bedragen, accountnamen of sleutels.
- Reproductie met 2.865 transacties, 66.403 dagkoersen en 138.157 koerswaarnemingen: versie 0.53.0 piekte op circa 1.153 MiB en hield geen overzichtcache vast. Dezelfde proef met deze versie piekte op circa 48 MiB en kon de cache hergebruiken. Lokale proefmeting, geen garantie voor iedere installatie.

## 0.53.0 · 2 november 2026

- Instellingen > Statistieken toont app-CPU, proces- en containergeheugen, de RAM-cache, database, databaselog, back-ups, vrije opslag en aantallen boekingen/koersen. Alleen admins hebben toegang; alleen de zichtbare pagina ververst.
- Home bouwt niet langer eerst alle volledige positiehistories op voor een compact overzicht. Dagtotalen worden per positie verzameld; EUR- en rapportgrafieken verwerken positiehistories achtereenvolgens.
- Ook koersverversing, Home Assistant-sensoren en het vooraf laden van EUR-totalen gebruiken het compacte overzicht. De achtergrondtaak berekent geen volledige EUR-grafiek meer voor alleen de totalen.
- De RAM-cache telt Python-objecten mee in plaats van alleen JSON-grootte. Te grote histories worden niet opnieuw gekopieerd naar de databasecache; verouderde dashboardcaches worden bij de start verwijderd. Boekingen en koersgegevens blijven behouden.
- Vergelijkende proef met 237 posities en 1.036 dagen: procespiek circa 345 MiB in 0.52.0 tegenover 49 MiB met deze versie. Dit is een lokale proefmeting, geen garantie voor iedere installatie.

## 0.52.0 — 2 november 2026

- EUR-totalen worden los van de volledige grafiekhistorie berekend en kunnen de al geladen compacte portefeuille hergebruiken. De historische grafiek laadt daarna op de achtergrond.
- Omrekening hergebruikt dezelfde gedateerde wisselkoers binnen een berekening. De grafiekberekening bewaart alleen de gezamenlijke dagtotalen en niet nogmaals alle omgerekende positiehistorie.
- Grafiekfouten laten de bedragen staan en bieden een knop om alleen de grafiek opnieuw te laden. Grafiekverzoeken blokkeren de pagina niet met de algemene laadlaag.
- Ongewijzigde gegevens worden bij herladen hergebruikt. Verouderde antwoorden, accountwissels en uitloggen blijven afgevangen; er worden geen ontbrekende koersen of wisselkoersen ingevuld.

## 0.51.0 — 2 november 2026

- Herstelt de lege resultaatgrafiek bij een portefeuille met ontbrekende koersen, waaronder het gecombineerde EUR-overzicht.
- Beschikbare dagresultaten blijven zichtbaar. De winst en aankoopinleg gebruiken exact dezelfde bekende posities; onbekende posities worden niet als nul of als inleg zonder bijbehorende winst meegerekend.
- De grafiek vermeldt expliciet wanneer alleen bekende posities worden getoond en hoeveel posities ontbreken. Dagen zonder bruikbare waarden blijven leeg.

## 0.50.0 — 1 november 2026

- Onderliggende ETF-beleggingen zijn aanklikbaar op de fondsdetailpagina en in rapporten. Een eigen aandeelpagina toont de bron-ETF, de weging, peildatum en beschikbare bedrijfsinformatie, zonder fictieve aankopen of direct aandelenbezit aan te maken.
- Logo’s en omschrijvingen gebruiken ook fondsprofielen en een kortere informatiecache. Bekende ETF-aanbieders krijgen een herkenbaar logo en brongebonden samenvatting wanneer bedrijfsinformatie ontbreekt.
- Home krijgt een groene/rode resultaatgrafiek met vlakvulling, nulreferentie, resultaatbadge en extra perioden 1D, 5D en 5Y. De bestaande marktwaarde/kostprijsweergave blijft kiesbaar.
- Percentagegrafieken gebruiken de totale aankoopinleg, inclusief gerealiseerd resultaat en dividend. Ontbrekende gegevens blijven grafiekgaten; de grafiek is geen tijdgewogen perioderendement en verzint geen handelsvolumes.

## 0.49.0 — 1 november 2026

- Herstelt herkenning van Vanguard-fondsen met Accumulation in de naam en Invesco-fondsen met afwijkende beursticker, waaronder VWCE.DE, VUAA.L en EHDV.DE.
- Automatische iShares-bronherkenning via de officiële Britse en Duitse catalogi, met lokale tickers, controle van fondsvarianten en ondersteuning voor Duitse CSV-kolommen, datums en getallen.
- TMX en single-stock ETP’s krijgen een gerichte toelichting; aanbieders zonder automatische koppeling worden expliciet gemeld. Verwachte ontbrekende bronnen worden niet meer als technische storing gelogd.

## 0.48.0 — 1 november 2026

- Instellingen > Taken haalt ETF-samenstellingen voor alle brokeraccounts op de achtergrond op, met voortgang, stoppen en opnieuw proberen van ontbrekende of mislukte fondsen.
- Gratis automatische bronherkenning voor Invesco, VanEck en Vanguard via officiële fondscatalogi en ISIN, ticker of eenduidige naam; geen betaalde dienst of API-sleutel nodig.
- Volledige holdings worden gecontroleerd en blijvend opgeslagen, inclusief Vanguard-paginering. Beschikbare sectoren en landen werken door in de aandeelpagina en rapporten; ontbrekende indelingen blijven zichtbaar.
- Bestaande gegevens blijven behouden bij bronfouten. De takenpagina is alleen voor beheerders en doet bij laden geen externe aanvragen.

## 0.47.0 — 1 november 2026

- ETF-detailpagina toont de volledige beschikbare samenstelling met percentages, sector, categorie, land, bron en peildatum; zoeken en bladeren door alle regels.
- Algemene bronkoppeling en CSV-import per fonds, met dagelijkse broncontrole, blijvende opslag, behoud bij bronfouten en zichtbare ontbrekende of verouderde gegevens. EXV1.DE en IWDA.AS hebben een vooraf gekoppelde iShares-bron.
- Beschikbare fondswegingen werken door in de rapportgrafieken voor spreiding, sectoren en landen. Ieder rapport bevat de actuele ETF-uitsplitsing; historische winst, dividend en kosten blijven bij de geboekte ETF.
- Databaseversie 22 bewaart fondscomposities en neemt ze gevalideerd mee in back-ups en herstel. Er worden geen onderliggende transacties aangemaakt.

## 0.46.0 — 1 november 2026

- Je aandelen krijgt meer diepte met verhoogde kaarten, gelaagde sectorsymbolen en een ruimere indeling.
- Sectoren tonen herkenbare symbolen, een korte uitleg en het aandeel in de open beursnoteringen.
- Landen worden getoond op een interactieve wereldkaart met vlaggen, Europaweergave en aantallen per land; onbekende landen blijven zichtbaar in de lijst.

## 0.45.0 — 1 november 2026

- Portefeuilleoverzicht staat altijd bovenaan de rapportenlijst.
- Gecombineerd EUR-dashboard met zes grafieken, vier kerncijfers en concentratie-inzicht; valuta-uitsplitsing is optioneel.
- Filters voor aandeel, sector en open of gesloten posities, naast broker en bronvaluta.

## 0.44.0

- Bestaande transacties wijzigen inclusief brokeraccount, datum, aantal, prijs, kosten, btw en andere belastingen.
- Kosten afzonderlijk bewerken of expliciet aan een transactie koppelen; gekoppelde bedragen gaan mee met broker- en datumcorrecties.
- Bewaar bronreferenties en volledige wijzigingshistorie. Voorkom dubbele kosten na herimport en verouderde overschrijvingen.
- Databaseversie 21 bewaart kostenkoppelingen en ondersteunt wijzigingshistorie voor losse kosten; bestaande administratie en back-ups blijven behouden.

## 0.43.2 — 31 oktober 2026

- Bij handmatige transacties in een andere handelsvaluta verschijnt een optioneel veld Prijs per aandeel in EUR. JavaScript rekent automatisch om na het kiezen van de transactiedatum; handmatig opnieuw omrekenen blijft mogelijk.
- De koersdatum en factor zijn zichtbaar. Gewijzigde invoer, datum of aandeel maakt een eerdere omrekening ongeldig; ontbrekende koersen krijgen geen 1:1-fallback.
- De server controleert de omrekening opnieuw en bewaart het oorspronkelijke EUR-bedrag, de handelsprijs en de gebruikte koers bij de transactie. Ook GBX/pence wordt ondersteund.
- De omrekening en eventuele kosten worden samen met de transactie opgeslagen. Databaseschema blijft 20.

## 0.43.1 — 31 oktober 2026

- Handmatige transacties hebben direct velden voor kosten exclusief btw, btw en een optionele eigen kostenvaluta. Het formulier ondersteunt aankoop en verkoop.
- Transactie en kosten worden samen opgeslagen, met hetzelfde brokeraccount en dezelfde datum en met een controleerbare verwijzing naar de transactie. Ongeldige invoer of een mislukte verkoop laat geen gedeeltelijke boeking achter.
- Kosten en btw komen direct in de kostenrapporten en het netto Rendementsoverzicht. De oorspronkelijke prijs per aandeel blijft behouden.
- Servercontrole op beheerdersrechten en sessiebeveiliging geldt ook voor handmatige transacties. Databaseschema blijft 20.

## 0.42.1 — 31 oktober 2026

- Bedrijfscijfers worden uitsluitend getoond bij ondersteunde Amerikaanse USD-noteringen. Bij andere beurzen en valuta's blijft het volledige onderdeel verborgen en wordt Defeat Beta niet opgevraagd.
- De server bepaalt de ondersteunde notering met dezelfde controle als de databron. Amerikaanse beursnoteringen van buitenlandse bedrijven blijven ondersteund; het vestigingsland is niet bepalend.

## 0.43.0 — 31 oktober 2026

- Kosten en belastingen krijgen een eigen administratie per brokeraccount: transactiekosten, bewaarloon, valutakosten, btw en overige belastingen, inclusief terugbetalingen.
- Brokerimports bewaren expliciete kostenvelden en losse kostenregels. Reeds netto verwerkte inhoudingen tellen niet dubbel; onduidelijke valuta, negatieve kostenkolommen en btw-inclusie blijven ter beoordeling.
- Nieuwe rapporten Kosten en belastingen en Belastingoverzicht: gecombineerd EUR-totaal, uitsplitsing per bronvaluta, soort en maand, originele bedragen, koersdatums en CSV-export voor ingelogde admins.
- Het Rendementsoverzicht neemt aanvullende kosten mee in totaalresultaat, jaarresultaten en XIRR. De oorspronkelijke aandelenkostprijs blijft behouden.
- Ontbrekende bedragen kunnen met bronreferentie via een pop-up of aanvullend CSV-sjabloon worden geboekt. Opnieuw importeren kan gemiste kosten aanvullen zonder dubbele transacties; expliciete oversla-keuzes blijven behouden.
- Databaseschema 20 voegt kostenboekingen en cache-invalidatie toe, met migratieback-up, gevalideerd herstel en rekeninggebonden verwijdering. Oudere boekingen worden niet herschreven.

## 0.42.0 — 31 oktober 2026

- Defeat Beta toegevoegd als aanvullende bron voor jaarcijfers op de aandelendetailpagina: omzet, nettowinst, operationele en vrije kasstroom en nettomarge voor maximaal vier boekjaren.
- Alleen ondersteunde Amerikaanse USD-noteringen worden gekoppeld. Rapportagevaluta, boekjaar, datasetdatum en ophaalmoment zijn zichtbaar. Ontbrekende cijfers blijven onbekend; bedrijfsgegevens wijzigen geen koersen of boekingen.
- Cijfers worden een dag bewaard in de bestaande SQLite-cache. Bij een bronstoring blijven eerdere cijfers met melding zichtbaar en geldt een wachttijd voor opnieuw ophalen.
- Nieuwe pagina Over ons met databronnen, bronlinks, dekking en actualiteit, kaart- en vlagverantwoording en gebruikte licenties. Beschikbaar in Nederlands, Engels en Spaans.
- De appcontainer gebruikt Debian slim met DuckDB en een vooraf geïnstalleerde officiële HTTP-uitbreiding voor het lezen van de openbare dataset. Geen databaseschemawijziging.

## 0.41.2

- Brokeraccount verwijderen en aanpassen wachten niet meer op het ophalen van koersen.
- Bij een lopende API-import of administratiebewerking verschijnt direct een melding; een verwijderactie blijft niet in de wachtrij staan.
- Verwijderaanvragen hebben een tijdslimiet. Bij ontbrekende bevestiging wordt gevraagd eerst de rekeninglijst te controleren.
- Bevestiging, herstelback-up, rechtencontrole en behoud van andere rekeningen blijven behouden.

## 0.41.1

- Revolut: bewaarloon en exact tegengestelde dividendbelastingcorrecties blokkeren de import niet meer; kapitaalterugbetalingen blijven buiten dividendwinst.
- De ServiceNow-splitsing van 18 december 2025 wordt met de bevestigde verhouding en het voorafgaande bezit gecontroleerd, met behoud van kostprijs.
- Exacte Amerikaanse tickers, Duitse beurscodes en de Allianz-WKN worden rechtstreeks gecontroleerd wanneer de zoekindex tekortschiet. Valuta en provider-wachttijden blijven gecontroleerd.
- Fusies en onbekende splitsingen krijgen gerichte beoordelingsmeldingen. Bestaande foutregels kunnen opnieuw worden verwerkt met behoud van bron-ID en handmatige keuzes.
- Databaseschema blijft 19; geen wijziging aan eerder geboekte transacties.

## 0.41.0

- Brokeraccounts aanpassen en verwijderen via Instellingen → Brokeraccounts, met aparte pop-ups.
- Namen wijzigen behoudt transacties; broker wijzigen kan alleen zonder administratie of API-verbinding.
- Verwijderen toont vooraf de omvang, vraagt expliciete bevestiging en maakt een herstelback-up. Alleen de gekozen rekening, administratie en API-verbinding worden verwijderd.
- Servercontrole op beheerdersrechten, sessiebeveiliging en verouderde bewerk- of verwijdervoorbeelden. Databaseschema blijft 19.

## 0.40.1

- Brokerrekening direct vanuit de importpop-up toevoegen, met de juiste broker vooraf ingevuld.
- Na aanmaken wordt de nieuwe rekening geselecteerd en keert de upload terug met behoud van het gekozen bestand.
- Lege rekeningkeuze krijgt een duidelijke melding; een import zonder rekening kan niet worden gestart.

## 0.40.0

- Imports opgesplitst in een rustig brokeroverzicht, drie eigen brokerpagina’s, importvoorbeeld en importgeschiedenis.
- Stappenhandleidingen met lokale brokerlogo’s, vergrootbare schermafbeeldingen met fictieve gegevens en verwijzingen naar brokerhulp.
- CSV-upload en API-rapporten blijven in pop-ups; alle nieuwe schermteksten zijn beschikbaar in Nederlands, Engels en Spaans.
- Databaseschema blijft 19; bestaande importcontroles en transacties blijven behouden.

## 0.39.0

- Wensen en bugs volledig indienen binnen Home Invest, zonder GitHub-account, via een apart te hosten centrale meldservice.
- Coolify-container met GitHub App, eenmalige installatieactivering, intrekbare toegang, verzendlimieten en duurzame wachtrij.
- Versleutelde lokale verzending met expliciete toestemming voor openbaarmaking en bescherming tegen dubbele meldingen.
- Meldservice staat standaard uit totdat een HTTPS-adres, GitHub App en activering zijn ingericht. Databaseschema blijft 19.

## 0.38.0

- Aparte pagina Wensen & bugs met zoeken, type- en statusfilters en een tijdelijk opgeslagen GitHub-overzicht.
- Nieuwe melding via een pop-up; controleren en publiceren met het eigen GitHub-account, zonder schrijftoken in Home Invest.
- Geen automatische verzending van portefeuilledata, logs of accountgegevens.

## 0.37.0

- Menu-items met dezelfde rijafstand als Home Assistant.
- Landenverdeling zonder bovenste header en filterbalk; wereldkaart over de volle breedte.
- Interactieve landentabel met marktwaarde en weging onder iedere kaart.

## 0.36.0

- Home Assistant-menuvormgeving: consequente blauwe selectie, vetgedrukte hoofditems en gelijkmatige submenu’s.
- EUR-rapport en bronvaluta uit dezelfde gegevensversie, ook tijdens koersupdates.
- Concrete foutmelding en afgeschermde Log-ID bij een mislukte EUR-berekening.

## 0.35.0

- Zijbalk in Home Assistant-stijl met compacte rijen, Material-iconen en blauwe selectie.
- Exporteren onder Imports; Dashboard als eerste instelling; Valuta en Logs zonder icoon onder Instellingen.
- Aparte transactiepagina’s voor dividend en splitsingen/omzettingen.

## 0.34.0

- Instellingen en imports met subpagina’s; Logs onder Instellingen.
- CSV- en PDF-export van transacties per brokeraccount of alle accounts.
- Revolut beleggings-CSV met importvoorbeeld, ontdubbeling en beoordeling.

# 0.33.0

- Rendementsoverzicht staat direct onder Portefeuilleoverzicht in het rapportmenu. De aandelenkeuze bovenaan is verwijderd; broker-, valuta-, jaar- en periodekeuzes blijven beschikbaar waar ze relevant zijn.
- Algemene marktwaarde-/winstkaarten worden alleen nog op Portefeuilleoverzicht getoond. Andere rapporten tonen hun eigen analyses, zonder herhaalde algemene totalen of irrelevante dividend-/valutatoelichting.
- Landenverdeling toont een interactieve wereldkaart met ingekleurde landen, lokale SVG-vlaggen en percentages. Wereld- en Europaweergave, aanklikbare landen, toetsenbordbediening, bedragen en een landenlijst met gewichten.
- Landnamen en landcodes worden samengevoegd. Onbekende indelingen en landen zonder kaartlocatie blijven zichtbaar en tellen mee in de procentbasis. Verdeling volgt de opgeslagen indeling en marktwaarde, zonder fictieve doorkijk in fondsposities.
- Natural Earth-kaartgegevens en flag-icons-vlaggen zijn lokaal gebundeld; geen externe kaartdienst of overdracht van portefeuilledata. Nederlandse, Engelse en Spaanse schermteksten; mobiele en brede layouts. Geen databaseschemawijziging.

# 0.32.2

- Herstelt Rendementsrapport laden mislukt wanneer een achtergrondkoersupdate het gegevensnummer vernieuwt tussen het laden van de keuzelijst en het rapport. Het rapport gebruikt één consistente servermomentopname; oude filters, brokeraccounts en uitgelogde sessies blijven afgeschermd.
- De EUR-jaarberekening verwerkt alleen opgeslagen jaargrenzen en de huidige stand. Dagreeksen worden niet opnieuw opgebouwd. Bestaande bedragen, gedateerde FX, splitsingen, omboekingen, dividend en XIRR blijven behouden; neutrale splitsingen vereisen geen onnodige wisselkoers op de splitsingsdatum.
- Het rendementsrapport krijgt zestig seconden laadtijd op tragere apparaten. Overige rapporten houden hun bestaande limiet. Bij een fout wordt onderscheid gemaakt tussen verbinding, time-out en servermelding; onverwachte rekenfouten geven een veilig Log-ID.
- Nieuwe regressiecontroles voor gelijktijdige koersupdates, filterwissels, opnieuw proberen, uitloggen, foutdetails en gelijke jaarstanden ten opzichte van volledige dagberekeningen.

# 0.32.1

- Nieuw rapport Rendementsoverzicht met winst/verlies per kalenderjaar, aankoopbedragen, kapitaal en uitsplitsing van koersresultaat, netto dividend en gerealiseerde winst. Eerst het gecombineerde EUR-totaal, daarna per bronvaluta; broker-, aandeel- en valutafilters blijven gelden.
- Intern rendement (XIRR) op jaarbasis uit gedateerde beleggingsgeldstromen en de actuele eindwaarde, met een 365-dagenbasis. Niet-eenduidige uitkomsten, ontbrekende koersen/FX en onvolledige omboekselecties krijgen geen percentage.
- Kosten en belasting worden expliciet als niet afzonderlijk geregistreerd getoond. Exact tijdgewogen rendement blijft niet berekenbaar zolang waarderingen rond iedere externe geldstroom ontbreken. Geen geschatte nulbedragen of fictieve percentages.
- Jaarbalken met eerdere/latere jaren, toetsenborddetails, onderliggende cijfers en een brede, mobiele rapportindeling. Nederlandse, Engelse en Spaanse vertalingen. Berekeningen laden uitsluitend bij openen van dit rapport; geen databaseschemawijziging.

# 0.32.0

- Aparte pagina Instellingen → TMX omboeken naar TDT, ook bereikbaar vanuit het TMX-aandeel. Officiële VanEck-omruilverhouding 0,937630, met eigen ontvangen aantal en datum per brokeraccount.
- Omboekingen voegen twee gekoppelde gebeurtenissen toe. Oorspronkelijke aankopen, verkopen, dividend en koershistorie blijven behouden; kostprijs en inleg gaan mee zonder extra verkoopwinst of nieuwe inleg. Eerst controleren, daarna opslaan met herstelback-up. Reeds geïmporteerde TDT-aankopen en eventuele contante fractievergoedingen moeten apart worden gecontroleerd.
- Apollo LU3170240538 (PRIVATE, EUR) haalt automatisch de openbare koers op bij DivvyDiary, met controle op ISIN en valuta en een blijvende cache van zes uur. De bron vermeldt geen koersdatum: de app benoemt de datum expliciet als ophaalmoment. Geen verzonnen historische NAV-reeks; bij fouten blijft de vorige koers behouden. Handmatige waarderingen houden voorrang.
- Databaseschema 19 voegt omboekgegevens toe; upgrades maken vooraf een back-up. Herstel controleert beide gekoppelde boekingen. Servercontrole op adminrechten, CSRF, dubbele boekingen en gewijzigde voorbeelden; Nederlandse, Engelse en Spaanse schermteksten.

# 0.31.4

- Dashboard aanpassen schakelt nu een bewerkmodus op Home zelf in. Elk onderdeel krijgt een eigen versleepgreep, verplaatsknoppen en tandwiel voor de module-instellingen.
- Modules direct op het dashboard verplaatsen met muis, aanraking of pijltjestoetsen; automatisch scrollen tijdens het slepen. De cijfers en grafieken blijven zichtbaar tijdens het indelen.
- Zichtbaarheid en breedte per onderdeel aanpassen via het eigen tandwiel, met directe voorvertoning. Uitgeschakelde onderdelen blijven in de bewerkmodus als herkenbare, instelbare plekken beschikbaar.
- Indeling opslaan, Annuleren en Standaardindeling staan op het dashboard zelf. Annuleren en navigeren herstellen de opgeslagen indeling. De bestaande opslag per gebruiker en profiel blijft behouden.

# 0.31.3

- Home bestaat uit tien losse modules: valutakeuze, vier afzonderlijke cijferkaarten, koers- en valuta-informatie, grafiek, grootste posities, resultaten en positietabel.
- Iedere gebruiker kan via Dashboard aanpassen modules aan- of uitzetten, de volgorde wijzigen en kiezen voor kleine, halve of volle breedte. Verslepen werkt op desktop; verplaatsknoppen ondersteunen toetsenbord en mobiel.
- Indelingen worden op de server per loginaccount opgeslagen, apart voor demo en eigen portefeuille. Zonder loginaccounts geldt de indeling voor de gedeelde Home Assistant-toegang. Portefeuilleherstel behoudt de huidige indelingen.
- Wijzigingen worden pas na Indeling opslaan toegepast; Annuleren behoudt de vorige indeling. Een standaardindeling en herstelbare lege weergave zijn beschikbaar. Uitgeschakelde grafieken laden geen lange positiehistorie.
- Servercontrole op modules, breedtes, gebruikerssessie en CSRF. Persoonlijke indelingen worden niet opgenomen in gedeelde portefeuilleantwoorden of browseropslag. Geen databaseschemawijziging.

# 0.31.2

- Profielkeuze verplaatst naar Mijn account en een modale pop-up; bij gebruikers zonder loginaccount is de keuze ook beschikbaar naast de taal in de taalpopup.
- Demo haalt actuele Yahoo-providerkoersen op in een eigen achtergrondtaak met SQLite-cache, behoud van de laatst geslaagde koers en respect voor providerwachttijden. Koersen kunnen vertraagd zijn; transacties, dividend en daghistorie blijven fictieve voorbeelden.
- Beursnoteringen gebruiken de juiste marktsuffixen; Britse pence worden voor GBP-koersen omgerekend. Demogegevens blijven gescheiden van de eigen portefeuille.
- Demo wordt voorbereid op de achtergrond en niet dagelijks opnieuw opgebouwd. Bestaande demo en overzichtcaches blijven bruikbaar. Actuele eigen koersen worden vóór historie opgehaald.
- Grotere laadanimatie centraal in beeld op mobiel, tablet en desktop, met ondersteuning voor minder beweging.

# 0.31.1

- Portefeuilleopbouw indexeert koersen, transacties en dividend eenmaal in plaats van alle regels opnieuw te doorzoeken voor iedere positie.
- Home gebruikt afzonderlijk gecachete, compacte overzichten. Het euro-overzicht bewaart geen volledige aandeelhistories in de overzichtcache. Geselecteerde grafieken laden en rekenen alleen de gekozen posities om.
- Veelgebruikte cacheweergaven blijven in het geheugen beschikbaar bij paginawissels. Historische cijfers en brokerfilters blijven behouden.
- Nieuwe niet-blokkerende laadanimatie met een munt en grafiekbalken, inclusief langere-wachttijdmelding, ondersteuning voor minder beweging en correcte afhandeling van fouten en paginawissels.

# 0.31.0

- Permanent kiesbaar demoprofiel met een eigen databasebestand onder data/demo/portfolio.sqlite3, gescheiden van de echte portefeuille en loginaccounts.
- Demo met 10 brokers, 150 verschillende aandelen, 10 valuta’s, circa EUR 150.000 marktwaarde, twee jaar koershistorie, aankopen, verkopen en dividend. Alle bedragen en koersen zijn fictief.
- Compacte overdracht van scripts en grotere dashboardantwoorden vermindert het laden van uitgebreide demo’s.
- Profielkeuze in het linkermenu en een zichtbare demobanner. Wisselen herlaadt het profiel en voorkomt vermenging van lopende aanvragen.
- Demo is alleen-lezen en werkt zonder marktproviderverzoeken. De bestaande aanmelding blijft vereist. De demo wordt automatisch aangemaakt en ververst alleen zijn eigen voorbeeldgegevens.

# 0.30.2

- Eurototalen sluiten posities met ontbrekende of ongeldige brongegevens uit voordat ze worden omgerekend. Een fout in een positie, transactie of dividendregel laat geldige, onafhankelijke regels beschikbaar. Gebruikersgegevens blijven behouden.
- Ongeldige dividendbedragen, datums en wisselkoersen worden overgeslagen. Het rapport vermeldt dat het totaal onvolledig is.
- Rapportopmaak wordt samen met het hoofdstylesheet geleverd, zodat koppen boven hun bedragen blijven staan.

# 0.30.1

- Eurototalen berekenen alleen de actuele stand; volledige daghistorie wordt alleen voor Waardeontwikkeling opgebouwd. Historische kostprijs, verkopen, splitsingen en gedateerde wisselkoersen blijven behouden.
- Langzame rapportberekeningen blokkeren andere dashboardpagina’s niet langer via de gedeelde cache. Het lezen van rapportwisselkoersen wacht niet op de providervergrendeling.
- Rapportaanvragen stoppen na 15 seconden met een herhaaloptie. Verouderde aanvragen worden afgebroken en gewijzigde gegevens veroorzaken geen eindeloze herlaadlus.

# 0.30.0

- Alle rapporten beginnen met het totaal van alle geselecteerde valuta’s omgerekend naar EUR, gevolgd door de uitsplitsing per bronvaluta. Dit geldt ook voor grafieken, dividendkalender, waardehistorie en onderliggende cijfers.
- Dividend gebruikt opgeslagen wisselkoersen op de betaaldatum; kostprijs en gerealiseerd resultaat gebruiken historische transactiedatums. Marktwaarde gebruikt beschikbare recente wisselkoersen.
- Ontbrekende wisselkoersen worden overgeslagen en als onvolledig totaal aangegeven. Geen 1-op-1-fallback, providerverzoeken bij laden of schemawijziging.

# 0.29.1

- Rapportpagina’s gebruiken de volledige beschikbare breedte en schalen mee op desktop, tablet en mobiel. Grafieken hebben geen vaste minimumbreedte meer.
- Nieuwe dividendkalender met maandnavigatie, weekdagen, betaalmarkeringen en een detailagenda. Ontvangen en geschatte betalingen hebben eigen kleuren; selecteer een dag voor de uitkeringen en basisdatum.
- Op kleine schermen blijven de kalenderdagen compact en verschijnen de bedragen en aandelen in de agenda eronder.

# 0.29.0

- Elk rapport heeft een eigen pagina-adres; het linkermenu toont alle tien rapporten zodra Rapporten wordt geopend.
- Dividendkalender toont betaaldatums en aandelen, ontvangen bedragen en toekomstige schattingen met instelbare jaarlijkse groei (standaard 3%).
- Schattingen gebruiken betalingen uit de afgelopen twaalf maanden voor nog open posities. De basisdatum blijft zichtbaar; toekomstige datums zijn indicatief en aangekondigde uitkeringen zijn niet gekoppeld.

# 0.28.0

- Professioneel rapportencentrum met tien analyses: overzicht, waardeontwikkeling, spreiding, winnaars en verliezers, resultaatopbouw, maanddividend, dividendbetalers, dividendkalender, sectoren en landen.
- Zeven interactieve grafiekvormen met details via muis en toetsenbord: donut, staaf, waterval, maandkolommen, lijn/oppervlak, resultaattegels en kalenderheatmap.
- Broker-, aandeel-, valuta-, jaar- en periodefilters, samenvattingskaarten en uitklapbare onderliggende cijfers. Valuta blijven gescheiden en ontbrekende gegevens worden overgeslagen.
- Waardehistorie wordt alleen bij openen van het rapport uit de lokale cache opgehaald; geen extra providerverzoeken of databaseschemaverandering.

# 0.27.1

- Rapporten slaan regels met ontbrekende koersen, bedragen of ongeldige gegevens over; geldige regels blijven berekend en zichtbaar.
- Toon het aantal overgeslagen regels en vermeld dat de totalen alleen de meegenomen regels bevatten. Bewaarde transacties blijven ongewijzigd.

# 0.27.0

- Vernieuwd rapportencentrum met portefeuille, resultaat per aandeel en dividend per maand of aandeel. Filters voor aandeel, valuta en dividendjaar binnen de gekozen broker.
- Actuele resultaten en jaarlijkse dividendcijfers blijven duidelijk gescheiden; valuta worden niet opgeteld.

## 0.26.2

- Onderaan het menu staat alleen de klikbare gebruikersnaam. Deze opent Mijn account met taalkeuze, account aanpassen en uitloggen.
- De gebruikerspagina werkt ook via het mobiele menu; accountwijzigingen blijven in een pop-up.

## 0.26.1

- Het accountmenu toont alleen de gebruikersnaam, zodat admin eenmaal verschijnt in plaats van admin · admin.

## 0.26.0

- Brokeraccount kiezen bovenaan Home, Aandelen en Dividend. Dezelfde keuze blijft actief bij het wisselen tussen pagina’s; Alle accounts toont het gezamenlijke overzicht.
- Aandelen, aantallen, waarde, winst, dividend, spreidingsgrafieken en categorievoortgang worden nu voor de gekozen brokeraccount berekend. Aandeeldetails volgen dezelfde selectie.
- Eerdere overzichten en lopende aanvragen worden bij een nieuwe brokerkeuze gewist of genegeerd, zodat gegevens van verschillende selecties niet worden gemengd.
- Nieuwe schermteksten beschikbaar in Nederlands, Engels en Spaans.

## 0.25.1

- Fondsen worden nu naast aandelen en ETF’s in de zoekresultaten getoond. Hierdoor kan Hybrid Index Fund NL-I worden toegevoegd door te zoeken op 0P0001IV37 en de gecontroleerde Yahoo-notering 0P0001IV37.F te kiezen.
- Zoekteksten verduidelijkt in Nederlands, Engels en Spaans. Valuta, notering, koers en historie blijven gecontroleerd via de bestaande koersdienst.

## 0.25.0 — 25 oktober 2026

- Nederlands, Engels en Spaans voor schermen, navigatie, formulieren, grafieken en meldingen.
- Bij de eerste start verschijnt een taalkeuze. Wijzig de taal later onder je account via Taal / Language / Idioma.
- De taal wordt per loginaccount opgeslagen en volgt het account op andere apparaten. Zonder aparte login geldt de opgeslagen voorkeur voor toegang via Home Assistant.
- Datums en bedragen volgen de gekozen taal. Eigen namen, notities, brontickers en gebruikersgegevens worden niet vertaald.
- Centrale vertaalcatalogus en automatische controle op ontbrekende talen bij nieuwe schermteksten.
- Databaseversie 18 voegt alleen een taalvoorkeur aan gebruikers toe, met vooraf een migratieback-up; bestaande portefeuillegegevens blijven behouden.

## 0.24.0

- Home Assistant kan de totale beleggingswaarde per oorspronkelijke valuta en het gezamenlijke totaal in euro ophalen via een aparte, alleen-lezen sensor-API.
- De sensorkoppeling is standaard uitgeschakeld. Een eigen toegangssleutel en optionele netwerkpoort beschermen de gegevens; het dashboard blijft via ingress bereikbaar.
- Instellingen toont actuele sensortotalen en passende REST-configuratie voor Home Assistant. Eén lokale aanvraag per minuut bedient alle sensoren vanuit de blijvende databasecache.
- Ontbrekende beurs- of wisselkoersen geven een onbekende waarde, met expliciete volledigheidsinformatie. Eurototalen gebruiken uitsluitend opgeslagen, gedateerde wisselkoersen; GBX wordt als pence omgerekend.
- De sensorwaarden zijn actuele beleggingswaarden over alle brokeraccounts; los brokersaldo en al uitgekeerd dividend worden niet nogmaals opgeteld. Databaseversie blijft 17.

## 0.23.0

- Home laadt uitsluitend opgeslagen portefeuillegegevens en wisselkoersen; externe koersaanvragen en ontbrekende historische valuta worden op de achtergrond bijgewerkt.
- Berekende overzichten worden gecomprimeerd in SQLite bewaard en in het geheugen hergebruikt, ook na een herstart. Revisies, appversie en dag voorkomen verouderde resultaten.
- Databaseversie 17 voegt een transactieve cache-revisie toe. Aankopen, dividend, koersen, historie, waarderingen, accounts, instellingen en FX-wijzigingen maken oude financiële overzichten ongeldig.
- De eerste paginarespons bevat de kerncijfers en totaalgrafieken; lange daghistorie wordt pas voor bekeken of vergeleken posities opgehaald, maximaal zes tegelijk.
- Verborgen rapporten en Home-tabellen worden niet bij iedere gegevensverversing opnieuw opgebouwd. Wisselen tussen valutakeuzes hergebruikt de reeds geladen euro-weergave.
- Historische wisselkoersen worden alleen voor ontbrekende perioden opgehaald; één nieuwe koers veroorzaakt geen nieuwe download van alle bekende koersjaren.
- Back-upherstel neemt geen berekende dashboardcaches over. Authenticatie blijft per aanvraag gecontroleerd; financiële gegevens en sessies worden niet in browseropslag bewaard.

## 0.22.2

- Trade Republic herkent CUSTOMER_INPAYMENT en geldbonussen zonder effecten als cashmutaties; ze tellen niet als aankoop of dividend.
- DELIVERY/MIGRATION wordt alleen overgeslagen bij een eenduidig gelijk uit-/inboekingspaar voor dezelfde ISIN, accountsoort, dag, valuta en prijs binnen één seconde. Onvolledige of afwijkende migraties blijven ter beoordeling.
- De bevestigde Netflix-splitsing van 17 november 2025 wordt gecontroleerd tegen het voorafgaande bezit en de 10-op-1-verhouding. Het bronbestand mag de extra aandelen of het nieuwe totaal bevatten; kostprijs, inleg en gerealiseerde winst blijven behouden.
- Een splitsing zonder geldvaluta gebruikt uitsluitend een eenduidige valuta uit dezelfde aankoophistorie of de opgeslagen ISIN-koppeling. Ontbrekende historie of een afwijkend aantal wordt niet geschat.
- Bestaande foutregels worden bij heropenen/opnieuw proberen opnieuw gecontroleerd met behoud van bron-ID’s, originele bronregels en handmatige beslissingen.

## 0.22.1

- Trade Republic: Private Markets-vooruitbetalingen zonder aantal/prijs worden als cashmutatie overgeslagen; de latere PRIVATE_FUND-aankoop gebruikt het expliciete aantal en de prijs.
- Apollo Global Private Markets ELTIF A2 UNH (LU3170240538) krijgt een eigen niet-beursgenoteerde ISIN-koppeling. Actuele fondswaardering is handmatig; er worden geen Yahoo-koersen of aankoophistorie als actuele waarde gebruikt.
- De boekdatum blijft behouden als de UTC-transactietijd op een aangrenzende dag valt. Beide bronvelden en bron-ID’s blijven ongewijzigd bewaard.
- Exacte, gecontroleerde EUR-noteringen toegevoegd voor Dividend 15 Split, BYD H, Rheinmetall, Xiaomi B en Alphabet A.
- Eerder afgewezen Trade Republic-regels worden bij heropenen of opnieuw proberen opnieuw gevalideerd met behoud van bronidentiteit en handmatige beslissingen. Herkende cashmutaties verdwijnen uit de openstaande beoordeling.
- Te beoordelen toont nu ook het Trade Republic-actietype en bronbedrag.
- Back-upherstel accepteert koppelingen van alle ondersteunde importaanbieders, inclusief Trade Republic, en blijft onbekende aanbieders weigeren.

## 0.22.0

- Imports krijgt een overzicht met brokerkaarten, duidelijke importstappen en een lege geschiedenis met uitleg. CSV-upload en API-rapportaanvraag openen in pop-ups.
- Nieuwe subpagina Imports → API-instellingen voor alle importaanbieders, met versleutelde Trading 212-verbindingen en uitleg over CSV bij Trade Republic.
- Trade Republic transactie-export CSV ondersteunt aankopen, verkopen en positief netto dividend voor aandelen en fondsen. Bron-ID’s, ISIN-koppelingen en ontdubbeling blijven per brokeraccount gescheiden.
- Onbekende acties, dividendcorrecties, ongeldige brongegevens en ontbrekende prijzen blijven duurzaam ter beoordeling; kostprijzen en corporate actions worden niet geschat.
- De beoordeling en heropening van importvoorbeelden gebruiken de adapter van de oorspronkelijke aanbieder.

## 0.21.2

- Alle pagina’s benutten de beschikbare schermbreedte; Home, Aandelen en Dividend hebben geen vaste maximumbreedte meer.
- Mobiele schermen krijgen passende kolommen, meeschalende velden en tabellen die binnen hun eigen paneel scrollen.
- Het zijmenu blijft ook op lage schermen volledig bereikbaar door te scrollen.

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
