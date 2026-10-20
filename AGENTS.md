# Projectafspraken

Bij iedere wijziging aan dit project:

- Houd appcode, dashboard, databestand en back-ups apart. Commit nooit gebruikersdata.
- Werk appversies bij in `portfolio/config.yaml` en `portfolio/app/version.py`.
- Als het databaseschema verandert: voeg de volgende opeenvolgende migratie toe
  in `portfolio/app/migrations.py` en verhoog `SCHEMA_VERSION`.
- Wijzig eerder gepubliceerde migraties niet. Een app-update zonder schemawijziging
  verhoogt alleen de appversie, niet de databaseversie.
- Laat de migratierunner de bestaande `PRAGMA user_version` controleren. Voer alleen
  ontbrekende stappen uit, maak vooraf een consistente back-up en voer upgrades
  transactioneel uit. Weiger een database uit een nieuwere versie.
- Test behoud van aankopen, dividend en historie bij upgrades, herhaalde start en
  rollback bij fouten. Voeg regressietests toe voor elke nieuwe migratie.
- Controleer de betrokken pagina's in de browser en voer passende bestaande tests uit.
- Werk README, DOCS en CHANGELOG bij wanneer gebruik of installatie verandert.
- Dwing accountrollen en CSRF op de server af; verborgen menu's zijn geen toegangscontrole.
- Importeer bij portefeuilleherstel nooit gebruikers, beveiligingsopties of uitvoerbaar
  schema uit een upload. Behoud de huidige accounts en maak vooraf een veiligheidskopie.
- Maak de overzichtcache ongeldig na mutaties, koersupdates en herstel. Cache geen
  sessies of financiële antwoorden in browseropslag; gebruik versiegebonden asset-URL's.
- Brokeraccounts zijn geen loginaccounts. Boek transacties en dividend per brokeraccount;
  deel marktdata alleen per instrument/beurs/valuta. Bestaande gegevens niet stilzwijgend
  aan een specifieke broker toeschrijven.
- Nieuwe importaanbieders krijgen een aparte adapter. Behoud previews, atomair importeren,
  bron-ID's en deduplicatie per account. Onbekende acties of ontbrekende kostprijs niet gokken.
- Bewaar succesvolle providerantwoorden in de SQLite-cache met passende TTL en haal oude
  historie incrementeel op. Sla geen API-sleutels of wachtwoorden op in providerpayloads.

- Gebruik diagnostics.py voor diagnostiek; sla nooit credentials, volledige headers, CSV-inhoud
  of ongefilterde responsebodies/tracebacks op. Logs en exports vereisen een ingelogde admin.

- Valuta: gebruik Decimal en de transactiedatum; gebruik geen toekomstige koers of een 1:1-fallback.
  GBX/GBp is pence (0,01 GBP). Behoud originele bedragen en de omrekenfactor/koersdatum.
  Ontbrekende FX houdt de betrokken regel apart; nieuwe FX-tabellen moeten in back-upherstel worden gevalideerd.

- Bewaar importkoppelingen blijvend per brokeraccount/aanbieder en ISIN of bronticker plus bronvaluta.
  Handmatige correcties winnen van automatische resultaten; herschrijf nooit stilzwijgend geboekte transacties.
  De beheerpagina mag geen provider oproepen bij het laden of lokaal zoeken. Respecteer provider-wachttijden.

- De gebruikersimport boekt geldige regels en bewaart fouten duurzaam in import_issues.
  Gebruik een savepoint per regel; ongeldige verkopen en ontbrekende FX mogen geen half geboekte regel achterlaten.
  Vraag om classificatie bij onbekende acties; kapitaalterugbetalingen zijn geen dividendwinst.
