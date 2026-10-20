# Home Invest — Gebruik

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
