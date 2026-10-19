# Home Invest — Gebruik

Gebruik het menu links: **Home**, **Aandelen**, **Dividend**, **Rapporten** en
**Instellingen**. Op een klein scherm verschijnt een menuknop. Home toont het
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
