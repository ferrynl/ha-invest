# Home Invest: fase 5 en 6

## Fase 5: voorspelbare prestaties
- Koersverversing bouwt één index met de oudste aankoopdatum per symbool/beurs/valuta.
- Omboekingsverkopen worden één keer geïndexeerd, in plaats van per positie alle transacties opnieuw door te lopen.
- Een ontbrekende aankoopdatum onderbreekt niet de volledige verversing.
- Regressietests controleren meerdere valuta's, omboekingen en 10.000 transacties.

De optimalisatie hoort geen boekingen, koersberekeningen of gebruikersgegevens te veranderen.

## Fase 6: releasebeveiliging zonder dubbele CI
De bestaande GitHub Actions workflow `Checks` is de centrale controle. Deze doet al:
- Python- en JavaScript-tests, lint en vertaalcontroles
- Releaseversie- en release-notitievalidatie via `scripts/release_notes.py`
- Browser smoke tests en Docker-builds van de app en feedbackservice
- Offline upgrade-tests en Trivy-containerscans

`CodeQL` blijft een aparte beveiligingsanalyse voor Python en JavaScript.
De eerder toegevoegde `Release readiness` workflow en `tools/check_release.py`
zijn verwijderd omdat ze bestaande checks dubbel uitvoerden.

## Eén bron voor changelogs
`CHANGELOG.md` is de enige bron van waarheid.
De Home Assistant-add-on verwacht daarnaast `portfolio/CHANGELOG.md`.
Dit blijft bestaan als identieke kopie voor compatibiliteit, maar hoeft niet
handmatig te worden onderhouden.

Na aanpassen van `CHANGELOG.md`:

```sh
python scripts/sync_changelog.py
```

CI controleert automatisch met `python scripts/sync_changelog.py --check`
of de twee bestanden identiek zijn. Daarmee kan een afwijkende kopie niet
stilletjes worden meegenomen in een release.

## Veilige uitrol
1. Wacht tot de bestaande `Checks` en `CodeQL` succesvol zijn afgerond.
2. Merge de PR pas na de vereiste groene checks.
3. De bestaande `Checks` workflow publiceert op een push naar `main` automatisch
   een GitHub-release voor een nog niet gepubliceerde versie.
4. Voor een nieuwe add-onversie moeten `portfolio/app/version.py`,
   `portfolio/config.yaml` en de changelogsectie overeenkomen.
5. Controleer vervolgens de versie via `ha-apps` en voer de update uit in Home Assistant.
6. Controleer Health Center, back-up en koersverversing na installatie.

**Belangrijk:** een merge alleen publiceert geen nieuwe add-onversie als het
versienummer gelijk blijft aan een eerder gepubliceerde release.
