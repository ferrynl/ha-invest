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
- Releasevoorstel 0.70.33 staat in PR #39. Alleen als checks groen zijn samenvoegen en releasepublicatie controleren.
- **Nog niet afgevinkt:** echte Home Assistant-installatietest, back-up plus restore, login/logout en duurtest bij netwerk/domein, inclusief route-/autorisatieaudit van publieke deployments (#23, #32).
- Voor de fase mag 'compleet' pas worden gebruikt nadat deze acceptatiecontroles zijn geverifieerd. GitHub groen bewijst niet dat HA live is.
- Herinnering: maandag rond 08:00 (Europe/Amsterdam), 16 nov t/m 28 dec.

## Bij iedere nieuwe projectsessie
Lees dit document; bekijk actuele GitHub-issues, PRs, checks en release-status; pak hoogste open P0 op; update roadmap zodra afgerond en geverifieerd.