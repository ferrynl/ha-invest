# Fase 7 en 8: financiële controles en testdekking

## Fase 7: read-only financial quality
De nieuwe module `portfolio/financial_quality.py` is bedoeld als bouwsteen voor de financiële controles van Health Center. De module:
- markeert ongeldige transactiegegevens, onmogelijke jaartallen, niet-eindige aantallen en prijzen;
- meldt mogelijke dubbele imports via bron-ID en via boekingskenmerken, altijd per broker;
- kan verwachte aantallen vergelijken met opgegeven holdings;
- gebruikt `Decimal` om afrondingsverschillen in aantallen te voorkomen.

**Veiligheid:** er worden geen transacties of back-ups verwijderd, geen migraties uitgevoerd en geen verschillen automatisch gecorrigeerd. Mogelijke dubbele boekingen vereisen menselijke beoordeling. De vergelijking van aantallen mag alleen worden gebruikt wanneer de volledige historie bekend en verwerkt is, inclusief splits, transfers en omboekingen. De aanroepende app moet dat afdwingen. Geen losse API-route of UI-koppeling is in deze PR geactiveerd.

## Fase 8: regressietests
`tests/test_financial_quality.py` dekt:
- detectie van dubbelen zonder brokeroverschrijdende vals-positieven;
- ongeldige datums en niet-eindige numerieke waarden;
- brokerisolatie en `Decimal`-precisie;
- voorzichtig overslaan van niet-ondersteunde corporate actions;
- een batch van 10.000 records.

Draai: `python -m unittest discover -s tests`.

## Vervolg voor daadwerkelijke activering in Health Center
1. Breng de bestaande databasevelden en corporate-actionlogica in kaart.
2. Voeg een normalisatielaag toe zonder bestaande gegevens te veranderen.
3. Maak resultaten in Health Center zichtbaar met uitlegbare redenen en een link naar betrokken boekingen.
4. Test een anonieme kopie van echte importscenario's en controleer dat de checks geen verkopen, omboekingen of splits ten onrechte als bewezen dubbel aanmerken.
5. Laat de bestaande CI en release-readiness groen worden voor merge.

Deze PR is bewust een veilige eerste implementatie, niet de volledige live-integratie van fase 7 en 8.
