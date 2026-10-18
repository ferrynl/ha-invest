# Gebruik

Open de webinterface of schakel de zijbalk in. Typ minimaal twee letters in
**Zoek een aandeel** en kies een resultaat uit Amsterdam, Nasdaq of NYSE.
Naam, symbool, beurs en valuta worden automatisch ingevuld. Vul zelf aantal,
aankoopprijs en datum in. Koersen worden standaard iedere 15 minuten gecontroleerd.
Stel het interval in met `refresh_minutes` en herstart de app.

De grafiek haalt historische dagkoersen op vanaf je eerste aankoop. Kies **1W, 1M,
3M, 6M, YTD, 1Y of Alles**. Op dagen zonder handel loopt de laatst bekende koers
door. Beweeg over de grafiek voor een dagwaarde of open **Dagwaarden bekijken**.
Valuta worden apart gehouden.
Yahoo-koersen kunnen vertraagd zijn; de koerstijd staat bij elke positie.

Gebruik **Back-up downloaden** voor een losse SQLite-kopie. Neem deze app ook op
in je Home Assistant-back-ups. De app bewaart daarnaast maximaal 30 dagelijkse
kopieën op hetzelfde apparaat. Herstel de volledige app via Home Assistant Back-ups.

Deze eerste versie ondersteunt alleen aankopen. De uitgebreide installatie-,
opslag- en ontwikkelinstructies staan in de README van de repository.
