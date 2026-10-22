# Home Invest voor Home Assistant

Experimentele versie (0.11.0). Draait volledig als Home Assistant-app
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
toegang tot de app.

- **Home**: overzicht per valuta, posities zoeken/filteren en maximaal zes posities vergelijken.
- **Aandelen**: posities en transacties bekijken; handmatig aankopen toevoegen.
- **Dividend**: netto ontvangen dividend boeken en bekijken.
- **Valuta**: historische omrekening en opgeslagen dagreferentiekoersen.
- **Rapporten**: dividend per maand en portefeuillestand.
- **Imports** (admin): Trading 212 CSV/API, beurskoppelingen en regels ter beoordeling.
- **Instellingen** (admin): accounts, beveiliging, back-ups en versiecontrole.
- **Logs** (admin): afgeschermde foutdetails en Log-ID zoeken.

Koersen komen van Yahoo Finance en kunnen vertraagd of tijdelijk onbeschikbaar zijn.
Bedragen in verschillende valuta blijven gescheiden. De app voert geen orders uit.

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

De database en instellingen staan in de app-datafolder. Appversie **0.11.0** gebruikt
databaseschema **11**. Upgrades maken vooraf een consistente back-up en voeren alleen
ontbrekende migraties transactioneel uit. Bestaande aankopen, dividend en historie blijven
behouden. Neem voor opgeslagen API-verbindingen de volledige app op in een Home Assistant-back-up.

Gebruikersdata, back-ups en API-sleutels horen niet in deze repository.

## Documentatie en ontwikkeling

- [Uitgebreide handleiding](portfolio/DOCS.md): installatie, gebruik, API, beveiliging,
  opslag en ontwikkelinstructies.
- [Changelog](CHANGELOG.md): versiegeschiedenis. Nieuwe wijzigingen worden hier bijgehouden.
- [Projectafspraken](AGENTS.md): afspraken voor onderhoud.

Tests uitvoeren vanuit de repository: python -m unittest discover -s tests.
De grafiek- en Home-controles staan in tests/test_chart.cjs en tests/test_home.cjs.
