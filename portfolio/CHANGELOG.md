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

