# 0.7.3

- Dividendontvangsten zonder lokale voorafgaande aankoop apart importeren met expliciete melding over ontbrekende aankoophistorie.
- Geen fictieve aankoop of kostprijs; brokeraccount, brongegevens, valutaomrekening en deduplicatie blijven behouden.
- Aantal van deze ontvangsten tonen na import. Schema blijft 8.

# 0.7.2

- Euronext Brussel en automatische ISIN-koppelingen voor Altria/MO en Sofina/SOF.
- Zoekcache vernieuwd voor nieuwe beursondersteuning; concrete koppelfouten ook naast de opslagknop.
- UTF-8-codering hersteld voor importmeldingen; expliciete charset voor JavaScript. Schema blijft 8.

# 0.7.1

- Importknop blijft na automatische koppeling bedienbaar; fouten per bronregel en ontbrekende koppelingen staan direct bij de knop.
- Bevestiging, voortgang en fouten bij opslaan worden naast de importknop getoond. Ongeldige batches blijven veilig geblokkeerd.
- Schema blijft 8.

# 0.7.0

- Nieuwe pagina Valuta met beschikbaar valutaoverzicht, historische rekenmachine en opgeslagen koershistorie.
- Frankfurter dagreferentiekoersen blijvend opslaan; 6-uurlijkse controle en historische import per jaar.
- Correcte GBX/GBp-eenheid (pence), London/Swiss-beurzen en issuer-gebaseerde ISIN-hints voor VWCE, VUSA, VFEA en EQGB.
- Historische prijs- en dividendomrekening naar de gecontroleerde noteringsvaluta; brondata en omrekenregistratie behouden.
- Geen half geboekte import bij ontbrekende koersen; Decimal-berekeningen en expliciete koersdatums.
- Schema 8 met valutametadata, koersen, dekking en importomrekeningen; migratieback-up en gevalideerd herstel.

# 0.6.0

- Automatische importkoppeling via ISIN, ticker en gecontroleerde koersvaluta; geen keuze per aandeel meer.
- Broker-tickers normaliseren, ETF's meenemen en extra beurscodes ondersteunen.
- Koppelingen bewaren in SQLite en hergebruiken; onzekere resultaten en valuta-afwijkingen niet gokken.
- Opgeslagen importvoorbeelden opnieuw openen en automatisch laten koppelen.
- Nieuwe resolver- en open-endpoints alleen voor admins; bevestiging van volledige import blijft verplicht.
- Schema blijft 7; bestaande previews en API-verbindingen blijven behouden.

# 0.5.4

- Trading 212 CSV en API ondersteunen de datumkolom Time (UTC), naast Time.
- Reeds opgeslagen deelrapporten na deze fout lokaal hervatten zonder nieuwe API-aanvraag.
- Deelrapporten met verschillende datum- en aanvullende belastingkolommen combineren.
- Dubbele kolomnamen en tegenstrijdige tijdvelden blokkeren in plaats van gegevens te gokken.
- Bron-ID's en deduplicatie behouden bij de gebruikelijke tijdnotatie; schema blijft 7.

# 0.5.3

- Concrete lokale foutreden in de logmelding en details, in plaats van alleen ValueError.
- Herkenbare codes voor lopende/ontbrekende aanvragen, wachttijden, geweigerde downloadhosts en CSV-kolommen.
- Context met importstap, omgeving, rapportnummer, periode, voortgang en resterende wachttijd.
- Alleen expliciet veilige appmeldingen loggen; onbekende externe foutteksten blijven afgeschermd.
- Schema blijft 7; API-verbindingen en lopende meerjarige importplannen blijven behouden.

# 0.5.2

- Oplossing voor Trading 212 HTTP 400: rapportperioden mogen maximaal één jaar beslaan.
- Lange perioden automatisch opsplitsen in delen van maximaal 364 dagen, ook rond schrikkeljaren.
- Delen via statuscontrole na elkaar aanvragen en samenvoegen tot één volledig importvoorbeeld.
- Voortgang en opgehaalde rapporten blijven behouden na fouten en herstarten.
- Lege rapportperioden afhandelen zonder onnodige boekingen; bestaande bron-ID-deduplicatie blijft actief.
- Begindatum standaard 1 januari van het huidige jaar; kies voor volledige historie je eerste transactie.
- Schema blijft 7; geen databasemigratie of nieuwe API-sleutels nodig.

# 0.5.1

- Nieuwe pagina Logs voor ingelogde admins; servercontrole op bekijken en downloaden.
- Gedeelde loggingmodule, opgeslagen in SQLite met maximaal 7 dagen en 5.000 regels.
- Trading 212-fouten met HTTP-status en Log-ID; providerfout, periode, omgeving en requestdetails afgeschermd terugvinden.
- Zoeken op Log-ID/melding, filters, paginering en JSON-download van de getoonde pagina.
- Centrale filtering van credentials, geheime velden, autorisatie, e-mailadressen en URL's.
- Ook logging voor marktdatafouten, achtergrondtaken en afgewezen app-aanvragen.
- Schema 7 voegt de logtabel toe; transactionele migratie met veiligheidsback-up.

# 0.5.0

- Trading 212 API-verbinding per brokeraccount, voor Live en Demo.
- Rapport aanvragen, later ophalen en controleren via dezelfde importpreview als CSV.
- Alleen admin met ingeschakelde gebruikersbeveiliging; CSRF op iedere actie.
- Sleutels versleuteld buiten SQLite, lokale encryptiesleutel en beperkte bestandsrechten.
- Rapportstatus en downloads in SQLite-cache, aanvraagbegrenzing en taakbehoud na herstart.
- Credentials nooit naar downloadhosts; vaste API-hosts, HTTPS-downloadcontrole en geen redirects.
- API- en CSV-imports delen bron-ID-controle; bestaande importbeperkingen blijven gelden.
- Database blijft schema 6; geen migratie nodig. Nieuwe cryptography-afhankelijkheid.

# 0.4.0

- Blijvende API-cache in SQLite, zoekdata een week en versiecontrole een dag gecachet.
- Historie incrementeel aanvullen; beurskoersen delen tussen brokeraccounts.
- Meerdere brokeraccounts, rekeningfilter en accountkoppeling bij transacties/dividend.
- Nieuwe uitbreidbare importmodule met Trading 212 History CSV-adapter.
- Preview, expliciete beurskoppeling, transactiecontrole en deduplicatie per rekening.
- Geïmporteerde verkopen verwerken met gemiddelde kostprijs en gerealiseerde winst.
- Versiecontrole onder Instellingen; installeren blijft via Home Assistant lopen.
- Schema 6; bestaande invoer blijft behouden onder Handmatig. Back-ups bevatten ook accounts, importregister en API-cache.

# 0.3.1

- Gebruikershoek linksonder in het zijmenu; accountbediening rechtsboven verwijderd.
- Account aanpassen met eigen gebruikersnaam en optioneel nieuw wachtwoord.
- Huidig wachtwoord verplicht, rol blijft behouden en na wijziging opnieuw aanmelden.
- Inlogknop in de gebruikershoek wanneer je bent uitgelogd.

# 0.3.0

- Back-up downloaden alleen onder Instellingen; gevalideerd terugzetten met veiligheidskopie vooraf.
- Gebruikersbeveiliging inschakelbaar onder Instellingen; eigen eerste admin, geen standaardwachtwoorden.
- Admin- en basicrollen, servercontrole, gebruikersbeheer, accountdeactivering en wachtwoordwijziging.
- PBKDF2-wachtwoordhashes, HttpOnly-sessies, sessieverloop, CSRF-controle en inlogbegrenzing.
- Herstel behoudt huidige accounts en rollen en meldt actieve sessies af.
- Servercache, ETags, versiegebonden assetcache en hergebruik van recente koersen.
- Schema 5 voegt accounts en de beveiligingsoptie toe; bestaande gegevens blijven behouden.

# 0.2.1

- De app heet overal Home Invest: app store, HA-zijbalk, menu, browsertitels en documentatie.

# 0.2.0

- Linkerzijbalk met Home, Aandelen, Dividend, Rapporten en Instellingen.
- Afzonderlijke paginaweergaven met directe links en ondersteuning voor terug/herladen.
- Inklapbaar menu op kleine schermen.
- Maandrapport voor dividend met jaarfilter en actuele portefeuilletotalen.
- Standaard grafiekperiode blijvend instelbaar.
- Geversioneerde databasemigraties met back-up vooraf en transactionele rollback.
- Schema 4 voegt dashboardinstellingen toe; bestaande schema's 1, 2 en 3 worden automatisch bijgewerkt.

# 0.1.3

- Alle aandelen samen zichtbaar met een eigen procentuele winstlijn per aandeel.
- Portefeuilletotalen per valuta in de grafiek, met aparte lijn inclusief dividend.
- Ontvangen netto dividend apart boeken met betaaldatum en notitie.
- Eigen dividendregister en SQLite-tabel, meegenomen in back-ups.
- Koerswinst, dividend en totale winst afzonderlijk zichtbaar, ook in daghistorie.

# 0.1.2

- Historische dagkoersen vanaf de aankoopdatum automatisch ophalen en opslaan.
- Elke kalenderdag zichtbaar, met laatst bekende koers op dagen zonder handel.
- Zoomknoppen 1W, 1M, 3M, 6M, YTD, 1Y en Alles.
- Grafiekassen, aanwijzen van dagwaardes en uitklapbare dagtabel.
- Bestaande databases worden uitgebreid met behoud van aankopen en back-ups.

# 0.1.1

- Zoek aandelen op naam of symbool vanaf twee tekens.
- Kies een resultaat om naam, symbool, beurs en valuta automatisch in te vullen.
- Ondersteunt Amsterdam, Nasdaq en NYSE; dubbele noteringen blijven herkenbaar.
- Korte zoekvertraging en cache beperken aanvragen; oude zoekresultaten worden genegeerd.

# 0.1.0

- Eerste experimentele versie met HA ingress-dashboard.
- Handmatige aankopen, SQLite, Yahoo-koersen en grafiek per aandeel.
- Gescheiden totalen per valuta, dagelijkse back-ups en download.

