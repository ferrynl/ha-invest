# Gebruik

Open de webinterface of schakel de zijbalk in. Voeg je aankopen toe met het juiste
Yahoo-symbool (Amsterdam: meestal `.AS`, VS: bijvoorbeeld `AAPL`). Kies beurs en
valuta van die notering. Koersen worden standaard iedere 15 minuten gecontroleerd.
Stel het interval in met `refresh_minutes` en herstart de app.

De grafiek begint bij de eerste opgeslagen koers. Valuta worden apart gehouden.
Yahoo-koersen kunnen vertraagd zijn; de koerstijd staat bij elke positie.

Gebruik **Back-up downloaden** voor een losse SQLite-kopie. Neem deze app ook op
in je Home Assistant-back-ups. De app bewaart daarnaast maximaal 30 dagelijkse
kopieën op hetzelfde apparaat. Herstel de volledige app via Home Assistant Back-ups.

Deze eerste versie ondersteunt alleen aankopen. De uitgebreide installatie-,
opslag- en ontwikkelinstructies staan in de README van de repository.
