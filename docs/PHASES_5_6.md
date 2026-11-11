# Home Invest: fase 5 en 6

## Fase 5: voorspelbare prestaties
- Koersverversing bouwt nu één index met de oudste aankoopdatum per symbool/beurs/valuta.
- Omboekingsverkopen worden één keer geïndexeerd, zodat de refresh geen volledige transactiescan per positie uitvoert.
- Ontbrekende aankoopdatums leiden tot een logmelding, niet tot een crash van de hele refresh.
- Regressietests controleren meerdere valuta's, omboekingen en 10.000 transacties.

Dit verandert geen boekingen, geen koersberekeningen en geen gebruikersgegevens.

## Fase 6: releasebeveiliging
De aparte GitHub Actions workflow `Release readiness` controleert bij pull requests:
1. Gelijke versienummers in `version.py` en `config.yaml`.
2. Changelogkoppen voor dezelfde versie.
3. Alle Python unittest-tests.
4. Een Docker-build van de Home Assistant-app.

De workflow heeft alleen leesrechten en publiceert of installeert **niets** automatisch.
Gebruik bij iedere nieuwe release eerst de controles. Merge alleen na groene checks,
controleer daarna de versie in ha-apps en test de update in Home Assistant.
Na de update: Health Center draaien, back-up verifiëren en koersverversing controleren.
Release tags en live-deploys blijven expliciete, afzonderlijke acties.
