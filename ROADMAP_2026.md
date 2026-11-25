# Home Invest | Roadmap tot 31 december 2026

**Centrale bron van waarheid voor dit ChatGPT-project en GitHub.** Voor actuele voortgang altijd open issues, PRs, CI en echte HA-installatie controleren. Een PR of merge is niet automatisch live.

## Principes

- P0: financiële onjuistheid, dataverlies, ongeautoriseerde toegang of kernfunctie die vastloopt. Blokkeert release.
- P1: belangrijke performance-, koers- en UX-problemen.
- P2: overige UX, documentatie, vindbaarheid.
- Behoud bestaande Python/Home Assistant/SQLite-basis tenzij gemeten bewijs een overstap rechtvaardigt.
- Back-up en rollback vóór risicovolle migraties. Geen stille mutaties van financiële data.
- Eén onderwerp per PR, automatische tests en expliciete acceptatie vóór merge.

## Zeven fases

| Fase | Periode (2026) | Thema | Onderwerpen | Gereed wanneer |
|---|---|---|---|---|
| 9 | 12–18 nov | Stabiliteit en security-baseline | Opslaghangs, foutafhandeling, fase 7/8 integratie, back-up en restore, audit endpoints | Geen oneindige spinners; herstel getest; P0 bevindingen getrieerd |
| 10 | 19–25 nov | Financiële datakwaliteit | Omboekingen, splitsingen, kosten, dividend, valuta, dubbele imports, brokerreconciliatie | Financiële regressies groen en anomalieën verklaard |
| 11 | 26 nov–2 dec | Performance en database | Profiling, indexen/WAL/busy timeout, caching, gecontroleerde koerstaken | Meetbare winst zonder inconsistente of oude koersgegevens |
| 12 | 3–9 dec | Mobiele interface en UX | Responsive dashboard, toegankelijkheid, zoeken, goede errors, onthouden velden | Kernflows betrouwbaar op telefoon, tablet en desktop |
| 13 | 10–16 dec | Koersen en Health Center | MNST/RYA/NEM1, beursdetectie, koersfallback, koersdatum en datakwaliteit | Symbolen vindbaar en reparaties transparant |
| 14 | 17–23 dec | Security en releasekwaliteit | Passkeys, cookies, autorisatie, CSRF, publieke domeinen, CI, duurtest, herstel | Geen kritieke securityrisico's, herstel- en regressietests groen |
| 15 | 24–31 dec | Feature freeze en 1.0 | Documentatie afmaken, testmatrix, releasecandidate, HA-update, rollback | 0 open P0, anders 1.0 doorschuiven |

## Parallelle werkstromen

### Technologie en performance
- Python 3.13, SQLite en DuckDB behouden totdat benchmarks anders aantonen.
- SQLite: PRAGMA-integriteit, WAL, locks, transacties, indexen, back-ups onderzoeken.
- DuckDB httpfs-uitbreiding op noodzaak onderzoeken; build zonder onnodige externe downloads waar mogelijk.
- Concurrency en lange achtergrondtaken profileren, eventueel gecontroleerde ASGI/FastAPI-verkenning.
- Pinned dependencies, container-scan, SBOM en geautomatiseerde updates met checks.

### Security voor lokaal, privé remote en publieke domeinen
- Alle API-routes en objecten op authenticatie en autorisatie controleren.
- HTTPS en reverse-proxyconfiguratie, secure cookies, sessies, CSRF, XSS/CSP, rate limits, passkeys en loginherstel testen.
- SQLite/database, back-ups en geheime tokens nooit op webpaden publiceren of in logs lekken.
- Encryptie van gevoelige data en sleutelbeheer beoordelen; herstelbaarheid waarborgen.
- Security Center met daadwerkelijke controles en herstelstappen, niet met fictieve scores.
- OWASP ASVS als auditbasis; VPN/tunnel voor privédomeinen aanbevelen.

### Officiële website + help
- Separate repo ferrynl/home-invest-site na bestaans-/toegangscheck.
- Voorkeur Astro Starlight: snel, statisch, NL/EN en documentatie via Markdown.
- Pagina's: Home, Features, Installatie, Docs, FAQ, Troubleshooting, Security/Privacy, Release notes, Roadmap, Community.
- Demo uitsluitend met fictieve data, nooit echte portefeuilles.
- Zoekfunctie, mobiel design, a11y, buildchecks, dead-link-checks.

### SEO en bekendheid
- GitHub README met duidelijke installatiestappen/screenshots/topics/releases.
- Echte probleemoplossende NL/EN-artikelen, met sitemap en metadata.
- Open-source community via Home Assistant-forum en geschikte Reddit-gemeenschappen zonder spam.
- Video/demo met fictieve portefeuille, feedback en meetbare verwijzingen.

## Acceptatiecriteria voor versie 1.0
- 0 open P0-issues en 100% gedefinieerde financiële regressies geslaagd.
- Dashboard met warme cache <= 2 sec en enkele transactie <= 1 sec in afgesproken representatieve testomgeving.
- 72 uur duurtest; back-up + restore + rollback aantoonbaar geslaagd.
- Autorisatie, API, passkeys, sessies en online-proxy-instellingen getest.
- Home Assistant Supervisor-test geslaagd, niet alleen CI.
- Nederlandse en Engelse installatie- en herstelhandleiding beschikbaar.
- 1.0 uitstellen als niet aan criteria is voldaan.

## Releaseprocedure
1. Ontwikkelen op branch en testen met fictieve data.
2. Tests, beveiligingschecks en review groen; changelog/versie consistent.
3. Merge naar main, bevestigen dat release en ha-apps updates daadwerkelijk beschikbaar zijn.
4. HA-installatie apart controleren; niet automatisch 'live' aannemen.

## Voortgang fase 9 (12 november)

- Fase 7/8 geïntegreerd in Health Center met regressietests (PR #21).
- Release 0.70.31 bevat expliciete bescherming tegen onduidelijke opslag-time-outs; 0.70.32 behandelt SQLite-locks veilig zonder financiële POST automatisch opnieuw uit te voeren.
- PR #33 is gemerged: configuratieregressietests voor HA-ingress en opt-in sensorpoort, plus docs/SECURE_REMOTE_ACCESS.md.
- PR #38 is gemerged, Checks/CodeQL/passkey-tests groen: sessiecontrole schrijft niet langer bij vrijwel iedere aanvraag naar SQLite.
- Release 0.70.33 is via PR #39 met groene Checks en CodeQL naar main gemerged; appstore-repository ferrynl/ha-apps is via PR #1 naar dezelfde versie bijgewerkt. Werkelijke installatie op de HA-host is niet bevestigd.
- **Nog niet afgevinkt:** echte Home Assistant-installatietest, back-up plus restore, login/logout en duurtest bij netwerk/domein, inclusief route-/autorisatieaudit van publieke deployments (#23, #32).
- Voor de fase mag 'compleet' pas worden gebruikt nadat deze acceptatiecontroles zijn geverifieerd. GitHub groen bewijst niet dat HA live is.
- Herinnering: maandag rond 08:00 (Europe/Amsterdam), 16 nov t/m 28 dec.

## Acceptatie fase 10 (17 november)

De [GitHub Checks voor PR #57](https://github.com/ferrynl/ha-invest/actions/runs/44017818767) draaiden de volledige Python-suite op de gewijzigde code. De regressies controleren:

- **Omboekingen en splitsingen:** kostprijs en historie blijven behouden. Ongeldige combinaties boeken geen halve transactie (`test_conversions.py`, `test_corporate_actions.py`).
- **Kosten en dividend:** kosten, btw en bronbelasting worden één keer verwerkt. Ontvangen dividend en prognoses blijven gescheiden (`test_charges.py`, `test_dividend_dashboard.py`).
- **Valuta:** de oorspronkelijke bedragen blijven bewaard. Een ontbrekende dagkoers houdt de boeking tegen; een toekomstige koers of 1:1 dient niet als fallback (`test_forex.py`).
- **Brokerreconciliatie:** de fictieve Trading 212-export met 100 aankopen en 9.900 dividendregels sluit aan op 25 aandelen, €3.000 kostprijs en €693 dividend. De 10.000 bron-ID’s worden per brokeraccount opgeslagen. Herimport boekt nul transacties. De IBKR-test controleert dezelfde bronidentiteit in CSV en XML (`test_broker_reconciliation.py`, `test_european_broker_imports.py`).
- **Verklaarde afwijkingen:** bron-ID’s met afwijkende inhoud, onbekende corporate actions en ontbrekende koersen of beurskoppelingen worden afgewezen of apart gehouden voor beoordeling. De geverifieerde EPIX.CVR-afwikkeling heeft een eigen regressietest. De mogelijke TMX → TDT-omzetting blijft ter beoordeling omdat de koppeling en over te dragen kostprijs niet zijn bevestigd (`test_partial_import.py`, `test_import_edge_cases.py`, PR #52).

De acceptatie gebruikt fictieve gegevens en geeft geen uitsluitsel over openstaande regels in een echte portefeuille. Home Invest 0.70.43 bevat de geteste appcode. PR #57 voegt de schaaltest toe aan GitHub Actions.

## Acceptatie fase 11 (25 november)

De reproduceerbare benchmark gebruikt een lokale HTTP-server met 10.000 fictieve aankopen, 10 brokers, 50 noteringen en 180 dagkoersen per notering. Hij meet de som van de twee warme dashboardrequests en de tijd van één bevestigde aankoop, telkens zeven keer. De releaseworkflow voert dezelfde benchmark uit in het containerimage. Start lokaal met `python scripts/benchmark_portfolio.py` na installatie van de appafhankelijkheden.

- In de lokale vergelijking met Python 3.12.14 en SQLite 3.53.1 daalde het eerste brokerdashboard van 231 ms naar 101 ms. De warmste representatieve dashboardreeks piekte op 118 ms (limiet 2 s) en een aankoop op 8 ms (limiet 1 s).
- SQLite gebruikt WAL zodat een langlopende lezer een writer niet blokkeert. Een regressietest bevestigt dat de writer commit terwijl de lezer zijn oorspronkelijke momentopname behoudt. De SQLite-wachttijd voor concurrerende schrijvers blijft 30 s. De HTTP-handler meldt een eventuele lock zonder de boeking opnieuw uit te voeren.
- De achtergrondtaak houdt één koersronde tegelijk aan. Gewijzigde koersen en historie verhogen de databaserevisie, zodat een volgende dashboardaanvraag nieuwe gegevens krijgt. De benchmark verifieert het behoud van de oorspronkelijke koersdatum en het zichtbaar worden van opgeslagen aankopen.
- De HTTP-server heeft al een limiet van 32 gelijktijdige verzoeken. DuckDB `httpfs` blijft nodig voor het opvragen van externe Parquet-data voor bedrijfsfundamentals. Die taak draait buiten het dashboardpad in een begrensd subprocess.
- Schema 28 voegt alleen indexen toe. Bij de eerste start op een bestaande database maakt de migratie een back-up. Gebruik voor teruggaan naar een versie met schema 27 een passende back-up van vóór de upgrade.
- Financiële controle tegen echte brokerexports blijft open in [#66](https://github.com/ferrynl/ha-invest/issues/66). De installatie, ingress en herstelproef op een echte Home Assistant-installatie blijven open in [#67](https://github.com/ferrynl/ha-invest/issues/67).

## Bij iedere nieuwe projectsessie
Lees dit document; bekijk actuele GitHub-issues, PRs, checks en release-status; pak hoogste open P0 op; update roadmap zodra afgerond en geverifieerd.
