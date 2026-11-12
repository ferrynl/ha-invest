# Fase 9 | Home Assistant acceptatieplan 0.70.33

Status: **voorbereid, nog niet op echte Home Assistant-installatie uitgevoerd**. Bijbehorende issues: [#23](https://github.com/ferrynl/ha-invest/issues/23) en [#32](https://github.com/ferrynl/ha-invest/issues/32).

## Doel en grenzen

Vaststellen dat de in GitHub gemergede verbeteringen in versie **0.70.33** ook in een echte Home Assistant OS/Supervisor-installatie werken. Het plan betreft installatie, sessies, databehoud, foutafhandeling, herstel, publieke domeinbeveiliging en logcontrole.

**Voer destructieve tests zoals 'Restore', verwijderen, resetten en moedwillige database-locks nooit uit op een productieportefeuille.** Maak een aparte testinstallatie met **fictieve gegevens**; gebruik geen persoonlijke portefeuille-export voor testbewijs. Herstel van echte data is uitsluitend een afzonderlijk, uitdrukkelijk goedgekeurd proces met een gecontroleerde back-up en stop-/rollbackplan.

## Vooraf: releasecontrole

- [ ] Controleer `ha-invest/portfolio/config.yaml`: versie `0.70.33`.
- [ ] Controleer `ha-apps/portfolio/config.yaml`: versie `0.70.33`.
- [ ] In Home Assistant: **Instellingen → Apps → App store** en de Home Invest-app openen. Ververs repository-informatie indien nodig.
- [ ] Noteer **daadwerkelijk geïnstalleerde** appversie, Home Assistant Core/Supervisor/OS-versie en browser. Alleen GitHub-versie of groene CI is onvoldoende.
- [ ] Controleer of de add-on-configuratie behouden is; sensorpoort `8100/tcp` hoort standaard op `null` tenzij bewust geactiveerd.
- [ ] Leg vóór een upgrade op de productie-installatie een actuele Home Assistant-back-up én een gecontroleerde Home Invest-back-up vast, en verifieer dat ze leesbaar/downloadbaar zijn. **De app-intern gemaakte SQLite-back-up is niet hetzelfde als een complete Home Assistant-back-up.**

## Risicoarm functioneel rooktestprotocol (echte installatie)

Registreer voor iedere test: datum/tijd, werkelijk versienummer, toegangsmethode (HA-ingress of vertrouwde HTTPS-host), resultaat PASS/FAIL/BLOCKED, foutmelding met Log-ID (geen persoonsgegevens/tokens).

| ID | Controle | Verwacht | Veilig op productie? |
|---|---|---|---|
| HA-01 | App start na update en toont versie 0.70.33 | Geen bootloop; juiste versie | Ja |
| HA-02 | Home-dashboard en aandelenoverzicht driemaal openen/herladen | Geen eindeloos laadscherm of 5xx | Ja |
| HA-03 | Health Center openen | SQLite-/back-up-/opslagstatus zichtbaar; waarschuwingen niet verhuld | Ja, alleen lezen |
| HA-04 | Admin login, uitloggen, opnieuw inloggen | Uitgelogde sessie heeft geen toegang meer | Ja, mits hersteltoegang beschikbaar |
| HA-05 | Gewone gebruiker opent adminfuncties (downloads, gebruikers, logs, wijzigacties) | 401/403 en geen data vrijgegeven | Ja, alleen toegang testen |
| HA-06 | Passkey-inlog (indien ingesteld), ook na herladen | Geslaagde login of verklaarde browser-/originbeperking | Ja, behoud wachtwoord |
| HA-07 | Dashboard en rapporten openen terwijl automatische koersverversing draait | Lezen blijft reageren; geen permanente spinner | Ja |
| HA-08 | Bestaande transacties openen, niets wijzigen | Geen fout of onverwachte datamutatie | Ja |
| HA-09 | Optionele sensor-API buiten ingestelde poort/geautoriseerde context | Geen onbevoegde toegang en geen publiek toegankelijke poort | Ja, vanaf eigen testomgeving |
| HA-10 | App/logs na upgrade controleren | Geen nieuwe kritieke fouten; log-ID’s helpen diagnose | Ja |

## Afgescheiden testomgeving met uitsluitend fictieve data

- [ ] Maak een tweede HA-testomgeving of geïsoleerde kopie met eigen app-data en testaccounts. Bevestig dat dit **niet** de productie-datadir of volumes zijn.
- [ ] TEST-01: boek een fictieve aankoop, een verkoop, dividend en kosten. Controleer broker, datum, aantal, valuta en resultaat en voorkom dubbel boeken.
- [ ] TEST-02: laat een transactie tijdens gesimuleerde SQLite-busy/lock mislukken. Verwacht een begrijpelijke foutstatus; controleer eerst transactielijst voordat opnieuw wordt opgeslagen. Geen automatische financiële POST-retry.
- [ ] TEST-03: maak back-up; controleer bestand en integriteit; zet uitsluitend deze fictieve back-up terug in de geïsoleerde testomgeving; controleer aantallen, rapporten, accounts en versie.
- [ ] TEST-04: simuleer herstel/rollback van 0.70.33 naar de eerder goedgekeurde versie in de **testomgeving**. Let op: oudere code kan niet zonder meer een nieuwere database openen; herstel daarom een passende pre-upgrade back-up.
- [ ] TEST-05: herhaal login/logout, passkeys en admin/gewone-gebruiker-toegang na restore.

## Domein- en beveiligingscontrole

- [ ] Controleer HTTPS, geldige certificaten en vertrouwde reverse-proxyconfiguratie.
- [ ] Controleer response cookies op `HttpOnly`, `SameSite` en `Secure` bij HTTPS; test niet met nep-`X-Forwarded-Proto` vanaf internet.
- [ ] Geen publieke `portfolio.sqlite3`, `/data`, back-ups, geheimen of poort `8100`.
- [ ] Admin-API's, back-ups, logs en imports vereisen correcte rollen en CSRF-voorwaarden.
- [ ] Proxy en publieke app-toegang alleen openhouden als auth-/sessiegedrag aantoonbaar juist is.
- [ ] Noteer uitsluitend geanonimiseerde testresultaten; nooit auth cookies, tokens, wachtwoorden, echte portefeuille-informatie of volledige privé-URL's in publieke GitHub Issues.

## Beslismoment

**PASS:** HA-01 t/m HA-10 volgens toepasselijkheid geslaagd, afgescheiden herstelproef geslaagd, geen P0-bevindingen, beveiligingsreview akkoord. Registreer bewijs en sluit issue #23 pas na verificatie.

**BLOCKED:** Geen toegang tot echte Supervisor of afgeschermde hersteltest → fase 9 blijft open. GitHub CI is geen vervanging.

**FAIL:** Dataverlies, onbevoegde toegang, dubbele boekingen, herhaalbaar vastlopen of onbetrouwbaar herstel → P0, nieuwe release blokkeren en zo nodig veilige rollback uitvoeren.

## Invulbaar resultaat

- Datum:
- Geïnstalleerde Home Invest-versie:
- HA Core / Supervisor / OS:
- Browser en toegangsmethode:
- Testomgeving: productie (alleen niet-destructief) / geïsoleerd (fictieve data)
- Geslaagd: ... / Mislukt: ... / Geblokkeerd: ...
- Log-ID's (zonder privédata):
- Opmerkingen:
- Besluit: PASS / BLOCKED / FAIL
- Getoetst door:
