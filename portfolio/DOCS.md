# Home Invest — Gebruik

**Nieuw in 0.7.0:** open **Valuta** voor omrekenen op datum naar bijvoorbeeld EUR,
het valutaoverzicht, opgeslagen koershistorie en importomrekeningen. Dagreferentiekoersen
worden in SQLite bewaard en iedere 6 uur gecontroleerd. GBX/GBp zijn Britse pence,
met exact 100 pence per GBP. Dit zijn dagreferentiekoersen, geen live brokerkoersen.

De automatische import herkent nu ook de ISIN-noteringen van VWCE, VUSA, VFEA en
EQGB en Londen/Zwitserland. Afwijkende aankoop- of dividendvaluta wordt met een
historische koers naar de gecontroleerde noteringsvaluta omgerekend, met behoud
van het origineel en de volledige omrekening. Ontbrekende koersen blokkeren de import.
Open je bestaande voorbeeld opnieuw; je hoeft geen nieuwe export te maken.
Database-upgrade naar schema 8 gebeurt met vooraf een veiligheidsback-up.

**Nieuw in 0.6.0:** beursnoteringen worden in de import automatisch gekoppeld op
basis van ISIN, ticker en valuta. Je hoeft niet per aandeel te zoeken of te kiezen.
Onder Importgeschiedenis kun je een opgeslagen voorbeeld openen en automatisch
laten koppelen. ETF's worden nu ook meegenomen. Een niet-eenduidige notering of
valutaverschil krijgt een concrete melding; bedragen worden niet omgerekend.
Controleer het complete voorbeeld en bevestig daarna één keer de import.


**Nieuw in 0.5.4:** CSV- en API-import ondersteunen `Time` en `Time (UTC)`.
Opgeslagen deelrapporten met de nieuwe kolomnaam kun je na bijwerken opnieuw laten
verwerken met **Rapportstatus controleren en ophalen**. Je hoeft geen nieuw rapport
aan te vragen of de lokale aanvraag te wissen. Bestaande transacties blijven behouden.

**Nieuw in 0.5.3:** lokale importmeldingen tonen nu de echte reden in Logs, met
`reason`, `code` en waar beschikbaar de stap, rapportvoortgang en resterende wachttijd.
Herhaal na de update de betreffende actie; oude regels met alleen ValueError kunnen
niet worden gereconstrueerd. Verbindingen en lopende aanvragen blijven behouden.

**Nieuw in 0.5.2:** Trading 212 accepteert maximaal één jaar per rapport. De app
splitst langere perioden automatisch in delen van maximaal 364 dagen. Controleer
ongeveer iedere minuut de rapportstatus: gereedstaande delen worden opgehaald en
het volgende deel wordt aangevraagd. Je ziet hoeveel rapporten al binnen zijn.
Pas na het laatste deel verschijnt één compleet importvoorbeeld. Voortgang blijft
bewaard na een fout of herstart. Kies als begindatum je eerste echte transactie.
De database blijft schema 7; bestaande verbindingen blijven bewaard.

**Nieuw in 0.5.1:** ingelogde admins krijgen de pagina **Logs**. Herhaal de mislukte
Trading 212-aanvraag na de update en zoek de Log-ID uit de foutmelding. Open details
voor HTTP-status, afgeschermde providerfout, omgeving en periode. Je kunt filteren,
oudere regels bekijken en de getoonde pagina downloaden. Logs blijven maximaal
7 dagen en 5.000 regels bewaard. API-sleutels en downloadadressen worden gefilterd.
De database gaat automatisch naar schema 7 met vooraf een veiligheidsback-up.

**Nieuw in 0.4.0:** maak bij Instellingen een brokeraccount aan, bijvoorbeeld met
bedrijf **Trading 212**. De rekeningkeuze bovenaan filtert je portefeuille.
Bestaande gegevens blijven onder **Handmatig** staan. Koersen worden gedeeld;
bezit, aankopen, verkopen en dividend blijven per rekening gescheiden.

Open als admin **Imports**, kies het brokeraccount en upload een Engelstalige
Trading 212 History CSV. Controleer het voorbeeld en de automatisch gekoppelde
beursnoteringen vóór bevestigen. Kooporders, verkooporders en dividend worden
ondersteund; dubbele brontransacties worden overgeslagen. Onbekende transactietypen,
ontbrekende aankopen of afwijkende dividendvaluta blokkeren de import. Kosten en
valutawissels worden nog niet meegenomen. Raadpleeg de README voor de precieze grenzen.
Vanaf 0.5.0 kun je ook via de Trading 212-API een rapport ophalen. Schakel gebruikersbeveiliging in en sla onder Imports de API key en secret op (alleen admin). Gebruik alleen rapportrechten. Kies de periode, vraag het rapport aan en controleer na een minuut de status. Daarna controleer en bevestig je hetzelfde importvoorbeeld. Sleutels staan versleuteld buiten SQLite; neem voor verbindingen de volledige app op in een HA-back-up. Er is nog geen automatische brokersynchronisatie.

Succesvolle API-antwoorden staan nu blijvend in SQLite. Zoekresultaten worden een
week hergebruikt en oudere dagkoersen blijven lokaal staan. Via **Instellingen →
Versiecontrole** controleer je de nieuwste GitHub-versie (één dag cache).

Linksonder in het zijmenu staat je gebruikershoek. Daar kun je je account aanpassen
(gebruikersnaam en/of wachtwoord), inloggen en uitloggen. Voor wijzigingen vul je
altijd je huidige wachtwoord in. Rechtsboven staan geen accountknoppen meer.

**Nieuw in 0.3.0:** back-up downloaden en terugzetten staan alleen onder
**Instellingen**. Bij terugzetten maak je een bevestigde keuze voor een SQLite-bestand
van maximaal 25 MB. Eerst wordt een veiligheidsback-up gemaakt. Accounts en rollen
blijven behouden; na herstel meld je je opnieuw aan.

Onder Instellingen kun je **Gebruikersbeveiliging** inschakelen met je eerste eigen
adminaccount (wachtwoord: 12–128 tekens). Admin heeft volledige toegang. Basic kan
de portefeuille, aankopen, dividend en rapporten gebruiken, maar geen instellingen,
accounts of back-ups. Accounts zijn voor dezelfde gedeelde portefeuille. Gebruik HA
via HTTPS en bewaar back-ups vertrouwelijk, want ze bevatten ook accountgegevens.

De app gebruikt nu servercache, ETags en versiegebonden browsercache. Koersen worden
niet bij iedere paginawisseling of invoer opnieuw bij Yahoo opgevraagd.

Gebruik het menu links: **Home**, **Aandelen**, **Dividend**, **Rapporten**, **Imports** en
**Instellingen** en **Logs**. Imports en Instellingen zijn voor admins; Logs vereist ook ingeschakelde gebruikersbeveiliging. Op een klein scherm verschijnt een menuknop. Home toont het
overzicht en de grafiek; invoer staat op de eigen pagina. Rapporten toont dividend
per maand en de huidige stand per valuta. Bij Instellingen kun je de standaard
grafiekperiode bewaren en de app- en databaseversie bekijken.

Database-updates worden op basis van de opgeslagen schemaversie uitgevoerd.
Alleen ontbrekende migraties worden toegepast. Vooraf wordt een extra back-up
gemaakt; bij fouten wordt de volledige migratie teruggedraaid. Bestaande aankopen,
dividend en koershistorie blijven behouden.

Open de webinterface of schakel de zijbalk in. Typ minimaal twee letters in
**Zoek een aandeel** en kies een resultaat uit Amsterdam, Nasdaq of NYSE.
Naam, symbool, beurs en valuta worden automatisch ingevuld. Vul zelf aantal,
aankoopprijs en datum in. Koersen worden standaard iedere 15 minuten gecontroleerd.
Stel het interval in met `refresh_minutes` en herstart de app.

De grafiek haalt historische dagkoersen op vanaf je eerste aankoop. Kies **1W, 1M,
3M, 6M, YTD, 1Y of Alles**. Op dagen zonder handel loopt de laatst bekende koers
door. Beweeg over de grafiek voor een dagwaarde of open **Dagwaarden bekijken**.
Valuta worden apart gehouden.
De standaardweergave toont alle aandelen met een lijn per aandeel in procenten,
inclusief ontvangen dividend. Kies **Totaal portefeuille · EUR/USD** voor het totaal
per valuta of selecteer één aandeel.

Onder **Ontvangen dividend** boek je het totale netto ontvangen bedrag en de
betaaldatum bij een bestaand aandeel. Gebruik de valuta die bij dat aandeel staat.
Het dividend staat apart en telt mee in **Totale winst**: koerswinst plus dividend.
Dividend wordt handmatig ingevoerd en niet automatisch herbelegd.
Yahoo-koersen kunnen vertraagd zijn; de koerstijd staat bij elke positie.

Gebruik **Back-up downloaden** voor een losse SQLite-kopie. Neem deze app ook op
in je Home Assistant-back-ups. De app bewaart daarnaast maximaal 30 dagelijkse
kopieën op hetzelfde apparaat. Herstel de volledige app via Home Assistant Back-ups.

Deze eerste versie ondersteunt alleen aankopen. De uitgebreide installatie-,
opslag- en ontwikkelinstructies staan in de README van de repository.

### Importknop (0.7.1)

Na de automatische koppeling is de opslagknop bedienbaar. Eventuele fouten per bronregel of ontbrekende koppelingen staan direct bij de knop. De bevestiging slaat deze controles niet over; corrigeer gemelde bronfouten voordat je opnieuw importeert. Fouten bij het opslaan verschijnen ook naast de knop. Schema blijft 8.

### Automatische koppeling MO en SOF (0.7.2)

Euronext Brussel wordt nu ondersteund. Gecontroleerde ISIN-koppelingen voor Altria (US02209S1033, MO in USD) en Sofina (BE0003717312, SOF.BR in EUR) werken ook bij onvolledige zoekresultaten. Afwijkende bronvaluta wordt via de bestaande historische omrekening verwerkt. Open je bestaande importvoorbeeld en klik Automatisch opnieuw koppelen. Schema blijft 8.

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
