## 0.42.1 — 31 oktober 2026

- Bedrijfscijfers worden uitsluitend getoond bij ondersteunde Amerikaanse USD-noteringen. Bij andere beurzen en valuta's blijft het volledige onderdeel verborgen en wordt Defeat Beta niet opgevraagd.
- De server bepaalt de ondersteunde notering met dezelfde controle als de databron. Amerikaanse beursnoteringen van buitenlandse bedrijven blijven ondersteund; het vestigingsland is niet bepalend.

## 0.42.0 — 31 oktober 2026

- Defeat Beta toegevoegd als aanvullende bron voor jaarcijfers op de aandelendetailpagina: omzet, nettowinst, operationele en vrije kasstroom en nettomarge voor maximaal vier boekjaren.
- Alleen ondersteunde Amerikaanse USD-noteringen worden gekoppeld. Rapportagevaluta, boekjaar, datasetdatum en ophaalmoment zijn zichtbaar. Ontbrekende cijfers blijven onbekend; bedrijfsgegevens wijzigen geen koersen of boekingen.
- Cijfers worden een dag bewaard in de bestaande SQLite-cache. Bij een bronstoring blijven eerdere cijfers met melding zichtbaar en geldt een wachttijd voor opnieuw ophalen.
- Nieuwe pagina Over ons met databronnen, bronlinks, dekking en actualiteit, kaart- en vlagverantwoording en gebruikte licenties. Beschikbaar in Nederlands, Engels en Spaans.
- De appcontainer gebruikt Debian slim met DuckDB en een vooraf geïnstalleerde officiële HTTP-uitbreiding voor het lezen van de openbare dataset. Geen databaseschemawijziging.

## 0.41.2

- Brokeraccount verwijderen en aanpassen wachten niet meer op het ophalen van koersen.
- Bij een lopende API-import of administratiebewerking verschijnt direct een melding; een verwijderactie blijft niet in de wachtrij staan.
- Verwijderaanvragen hebben een tijdslimiet. Bij ontbrekende bevestiging wordt gevraagd eerst de rekeninglijst te controleren.
- Bevestiging, herstelback-up, rechtencontrole en behoud van andere rekeningen blijven behouden.

## 0.41.1

- Revolut: bewaarloon en exact tegengestelde dividendbelastingcorrecties blokkeren de import niet meer; kapitaalterugbetalingen blijven buiten dividendwinst.
- De ServiceNow-splitsing van 18 december 2025 wordt met de bevestigde verhouding en het voorafgaande bezit gecontroleerd, met behoud van kostprijs.
- Exacte Amerikaanse tickers, Duitse beurscodes en de Allianz-WKN worden rechtstreeks gecontroleerd wanneer de zoekindex tekortschiet. Valuta en provider-wachttijden blijven gecontroleerd.
- Fusies en onbekende splitsingen krijgen gerichte beoordelingsmeldingen. Bestaande foutregels kunnen opnieuw worden verwerkt met behoud van bron-ID en handmatige keuzes.
- Databaseschema blijft 19; geen wijziging aan eerder geboekte transacties.

## 0.41.0

- Brokeraccounts aanpassen en verwijderen via Instellingen → Brokeraccounts, met aparte pop-ups.
- Namen wijzigen behoudt transacties; broker wijzigen kan alleen zonder administratie of API-verbinding.
- Verwijderen toont vooraf de omvang, vraagt expliciete bevestiging en maakt een herstelback-up. Alleen de gekozen rekening, administratie en API-verbinding worden verwijderd.
- Servercontrole op beheerdersrechten, sessiebeveiliging en verouderde bewerk- of verwijdervoorbeelden. Databaseschema blijft 19.

## 0.40.1

- Brokerrekening direct vanuit de importpop-up toevoegen, met de juiste broker vooraf ingevuld.
- Na aanmaken wordt de nieuwe rekening geselecteerd en keert de upload terug met behoud van het gekozen bestand.
- Lege rekeningkeuze krijgt een duidelijke melding; een import zonder rekening kan niet worden gestart.

## 0.40.0

- Imports opgesplitst in een rustig brokeroverzicht, drie eigen brokerpagina’s, importvoorbeeld en importgeschiedenis.
- Stappenhandleidingen met lokale brokerlogo’s, vergrootbare schermafbeeldingen met fictieve gegevens en verwijzingen naar brokerhulp.
- CSV-upload en API-rapporten blijven in pop-ups; alle nieuwe schermteksten zijn beschikbaar in Nederlands, Engels en Spaans.
- Databaseschema blijft 19; bestaande importcontroles en transacties blijven behouden.

## 0.39.0

- Wensen en bugs volledig indienen binnen Home Invest, zonder GitHub-account, via een apart te hosten centrale meldservice.
- Coolify-container met GitHub App, eenmalige installatieactivering, intrekbare toegang, verzendlimieten en duurzame wachtrij.
- Versleutelde lokale verzending met expliciete toestemming voor openbaarmaking en bescherming tegen dubbele meldingen.
- Meldservice staat standaard uit totdat een HTTPS-adres, GitHub App en activering zijn ingericht. Databaseschema blijft 19.

## 0.38.0

- Aparte pagina Wensen & bugs met zoeken, type- en statusfilters en een tijdelijk opgeslagen GitHub-overzicht.
- Nieuwe melding via een pop-up; controleren en publiceren met het eigen GitHub-account, zonder schrijftoken in Home Invest.
- Geen automatische verzending van portefeuilledata, logs of accountgegevens.

## 0.37.0

- Menu-items met dezelfde rijafstand als Home Assistant.
- Landenverdeling zonder bovenste header en filterbalk; wereldkaart over de volle breedte.
- Interactieve landentabel met marktwaarde en weging onder iedere kaart.

## 0.36.0

- Home Assistant-menuvormgeving: consequente blauwe selectie, vetgedrukte hoofditems en gelijkmatige submenu’s.
- EUR-rapport en bronvaluta uit dezelfde gegevensversie, ook tijdens koersupdates.
- Concrete foutmelding en afgeschermde Log-ID bij een mislukte EUR-berekening.

## 0.35.0

- Zijbalk in Home Assistant-stijl met compacte rijen, Material-iconen en blauwe selectie.
- Exporteren onder Imports; Dashboard als eerste instelling; Valuta en Logs zonder icoon onder Instellingen.
- Aparte transactiepagina’s voor dividend en splitsingen/omzettingen.

## 0.34.0

- Instellingen en imports met subpagina’s; Logs onder Instellingen.
- CSV- en PDF-export van transacties per brokeraccount of alle accounts.
- Revolut beleggings-CSV met importvoorbeeld, ontdubbeling en beoordeling.

# 0.33.0

- Rendementsoverzicht staat direct onder Portefeuilleoverzicht in het rapportmenu. De aandelenkeuze bovenaan is verwijderd; broker-, valuta-, jaar- en periodekeuzes blijven beschikbaar waar ze relevant zijn.
- Algemene marktwaarde-/winstkaarten worden alleen nog op Portefeuilleoverzicht getoond. Andere rapporten tonen hun eigen analyses, zonder herhaalde algemene totalen of irrelevante dividend-/valutatoelichting.
- Landenverdeling toont een interactieve wereldkaart met ingekleurde landen, lokale SVG-vlaggen en percentages. Wereld- en Europaweergave, aanklikbare landen, toetsenbordbediening, bedragen en een landenlijst met gewichten.
- Landnamen en landcodes worden samengevoegd. Onbekende indelingen en landen zonder kaartlocatie blijven zichtbaar en tellen mee in de procentbasis. Verdeling volgt de opgeslagen indeling en marktwaarde, zonder fictieve doorkijk in fondsposities.
- Natural Earth-kaartgegevens en flag-icons-vlaggen zijn lokaal gebundeld; geen externe kaartdienst of overdracht van portefeuilledata. Nederlandse, Engelse en Spaanse schermteksten; mobiele en brede layouts. Geen databaseschemawijziging.

# 0.32.2

- Herstelt Rendementsrapport laden mislukt wanneer een achtergrondkoersupdate het gegevensnummer vernieuwt tussen het laden van de keuzelijst en het rapport. Het rapport gebruikt één consistente servermomentopname; oude filters, brokeraccounts en uitgelogde sessies blijven afgeschermd.
- De EUR-jaarberekening verwerkt alleen opgeslagen jaargrenzen en de huidige stand. Dagreeksen worden niet opnieuw opgebouwd. Bestaande bedragen, gedateerde FX, splitsingen, omboekingen, dividend en XIRR blijven behouden; neutrale splitsingen vereisen geen onnodige wisselkoers op de splitsingsdatum.
- Het rendementsrapport krijgt zestig seconden laadtijd op tragere apparaten. Overige rapporten houden hun bestaande limiet. Bij een fout wordt onderscheid gemaakt tussen verbinding, time-out en servermelding; onverwachte rekenfouten geven een veilig Log-ID.
- Nieuwe regressiecontroles voor gelijktijdige koersupdates, filterwissels, opnieuw proberen, uitloggen, foutdetails en gelijke jaarstanden ten opzichte van volledige dagberekeningen.

# 0.32.1

- Nieuw rapport Rendementsoverzicht met winst/verlies per kalenderjaar, aankoopbedragen, kapitaal en uitsplitsing van koersresultaat, netto dividend en gerealiseerde winst. Eerst het gecombineerde EUR-totaal, daarna per bronvaluta; broker-, aandeel- en valutafilters blijven gelden.
- Intern rendement (XIRR) op jaarbasis uit gedateerde beleggingsgeldstromen en de actuele eindwaarde, met een 365-dagenbasis. Niet-eenduidige uitkomsten, ontbrekende koersen/FX en onvolledige omboekselecties krijgen geen percentage.
- Kosten en belasting worden expliciet als niet afzonderlijk geregistreerd getoond. Exact tijdgewogen rendement blijft niet berekenbaar zolang waarderingen rond iedere externe geldstroom ontbreken. Geen geschatte nulbedragen of fictieve percentages.
- Jaarbalken met eerdere/latere jaren, toetsenborddetails, onderliggende cijfers en een brede, mobiele rapportindeling. Nederlandse, Engelse en Spaanse vertalingen. Berekeningen laden uitsluitend bij openen van dit rapport; geen databaseschemawijziging.

# 0.32.0

- Aparte pagina Instellingen → TMX omboeken naar TDT, ook bereikbaar vanuit het TMX-aandeel. Officiële VanEck-omruilverhouding 0,937630, met eigen ontvangen aantal en datum per brokeraccount.
- Omboekingen voegen twee gekoppelde gebeurtenissen toe. Oorspronkelijke aankopen, verkopen, dividend en koershistorie blijven behouden; kostprijs en inleg gaan mee zonder extra verkoopwinst of nieuwe inleg. Eerst controleren, daarna opslaan met herstelback-up. Reeds geïmporteerde TDT-aankopen en eventuele contante fractievergoedingen moeten apart worden gecontroleerd.
- Apollo LU3170240538 (PRIVATE, EUR) haalt automatisch de openbare koers op bij DivvyDiary, met controle op ISIN en valuta en een blijvende cache van zes uur. De bron vermeldt geen koersdatum: de app benoemt de datum expliciet als ophaalmoment. Geen verzonnen historische NAV-reeks; bij fouten blijft de vorige koers behouden. Handmatige waarderingen houden voorrang.
- Databaseschema 19 voegt omboekgegevens toe; upgrades maken vooraf een back-up. Herstel controleert beide gekoppelde boekingen. Servercontrole op adminrechten, CSRF, dubbele boekingen en gewijzigde voorbeelden; Nederlandse, Engelse en Spaanse schermteksten.

# 0.31.4

- Dashboard aanpassen schakelt nu een bewerkmodus op Home zelf in. Elk onderdeel krijgt een eigen versleepgreep, verplaatsknoppen en tandwiel voor de module-instellingen.
- Modules direct op het dashboard verplaatsen met muis, aanraking of pijltjestoetsen; automatisch scrollen tijdens het slepen. De cijfers en grafieken blijven zichtbaar tijdens het indelen.
- Zichtbaarheid en breedte per onderdeel aanpassen via het eigen tandwiel, met directe voorvertoning. Uitgeschakelde onderdelen blijven in de bewerkmodus als herkenbare, instelbare plekken beschikbaar.
- Indeling opslaan, Annuleren en Standaardindeling staan op het dashboard zelf. Annuleren en navigeren herstellen de opgeslagen indeling. De bestaande opslag per gebruiker en profiel blijft behouden.

# 0.31.3

- Home bestaat uit tien losse modules: valutakeuze, vier afzonderlijke cijferkaarten, koers- en valuta-informatie, grafiek, grootste posities, resultaten en positietabel.
- Iedere gebruiker kan via Dashboard aanpassen modules aan- of uitzetten, de volgorde wijzigen en kiezen voor kleine, halve of volle breedte. Verslepen werkt op desktop; verplaatsknoppen ondersteunen toetsenbord en mobiel.
- Indelingen worden op de server per loginaccount opgeslagen, apart voor demo en eigen portefeuille. Zonder loginaccounts geldt de indeling voor de gedeelde Home Assistant-toegang. Portefeuilleherstel behoudt de huidige indelingen.
- Wijzigingen worden pas na Indeling opslaan toegepast; Annuleren behoudt de vorige indeling. Een standaardindeling en herstelbare lege weergave zijn beschikbaar. Uitgeschakelde grafieken laden geen lange positiehistorie.
- Servercontrole op modules, breedtes, gebruikerssessie en CSRF. Persoonlijke indelingen worden niet opgenomen in gedeelde portefeuilleantwoorden of browseropslag. Geen databaseschemawijziging.

# 0.31.2

- Profielkeuze verplaatst naar Mijn account en een modale pop-up; bij gebruikers zonder loginaccount is de keuze ook beschikbaar naast de taal in de taalpopup.
- Demo haalt actuele Yahoo-providerkoersen op in een eigen achtergrondtaak met SQLite-cache, behoud van de laatst geslaagde koers en respect voor providerwachttijden. Koersen kunnen vertraagd zijn; transacties, dividend en daghistorie blijven fictieve voorbeelden.
- Beursnoteringen gebruiken de juiste marktsuffixen; Britse pence worden voor GBP-koersen omgerekend. Demogegevens blijven gescheiden van de eigen portefeuille.
- Demo wordt voorbereid op de achtergrond en niet dagelijks opnieuw opgebouwd. Bestaande demo en overzichtcaches blijven bruikbaar. Actuele eigen koersen worden vóór historie opgehaald.
- Grotere laadanimatie centraal in beeld op mobiel, tablet en desktop, met ondersteuning voor minder beweging.

# 0.31.1

- Portefeuilleopbouw indexeert koersen, transacties en dividend eenmaal in plaats van alle regels opnieuw te doorzoeken voor iedere positie.
- Home gebruikt afzonderlijk gecachete, compacte overzichten. Het euro-overzicht bewaart geen volledige aandeelhistories in de overzichtcache. Geselecteerde grafieken laden en rekenen alleen de gekozen posities om.
- Veelgebruikte cacheweergaven blijven in het geheugen beschikbaar bij paginawissels. Historische cijfers en brokerfilters blijven behouden.
- Nieuwe niet-blokkerende laadanimatie met een munt en grafiekbalken, inclusief langere-wachttijdmelding, ondersteuning voor minder beweging en correcte afhandeling van fouten en paginawissels.

# 0.31.0

- Permanent kiesbaar demoprofiel met een eigen databasebestand onder data/demo/portfolio.sqlite3, gescheiden van de echte portefeuille en loginaccounts.
- Demo met 10 brokers, 150 verschillende aandelen, 10 valuta’s, circa EUR 150.000 marktwaarde, twee jaar koershistorie, aankopen, verkopen en dividend. Alle bedragen en koersen zijn fictief.
- Compacte overdracht van scripts en grotere dashboardantwoorden vermindert het laden van uitgebreide demo’s.
- Profielkeuze in het linkermenu en een zichtbare demobanner. Wisselen herlaadt het profiel en voorkomt vermenging van lopende aanvragen.
- Demo is alleen-lezen en werkt zonder marktproviderverzoeken. De bestaande aanmelding blijft vereist. De demo wordt automatisch aangemaakt en ververst alleen zijn eigen voorbeeldgegevens.

# 0.30.2

- Eurototalen sluiten posities met ontbrekende of ongeldige brongegevens uit voordat ze worden omgerekend. Een fout in een positie, transactie of dividendregel laat geldige, onafhankelijke regels beschikbaar. Gebruikersgegevens blijven behouden.
- Ongeldige dividendbedragen, datums en wisselkoersen worden overgeslagen. Het rapport vermeldt dat het totaal onvolledig is.
- Rapportopmaak wordt samen met het hoofdstylesheet geleverd, zodat koppen boven hun bedragen blijven staan.

# 0.30.1

- Eurototalen berekenen alleen de actuele stand; volledige daghistorie wordt alleen voor Waardeontwikkeling opgebouwd. Historische kostprijs, verkopen, splitsingen en gedateerde wisselkoersen blijven behouden.
- Langzame rapportberekeningen blokkeren andere dashboardpagina’s niet langer via de gedeelde cache. Het lezen van rapportwisselkoersen wacht niet op de providervergrendeling.
- Rapportaanvragen stoppen na 15 seconden met een herhaaloptie. Verouderde aanvragen worden afgebroken en gewijzigde gegevens veroorzaken geen eindeloze herlaadlus.

# 0.30.0

- Alle rapporten beginnen met het totaal van alle geselecteerde valuta’s omgerekend naar EUR, gevolgd door de uitsplitsing per bronvaluta. Dit geldt ook voor grafieken, dividendkalender, waardehistorie en onderliggende cijfers.
- Dividend gebruikt opgeslagen wisselkoersen op de betaaldatum; kostprijs en gerealiseerd resultaat gebruiken historische transactiedatums. Marktwaarde gebruikt beschikbare recente wisselkoersen.
- Ontbrekende wisselkoersen worden overgeslagen en als onvolledig totaal aangegeven. Geen 1-op-1-fallback, providerverzoeken bij laden of schemawijziging.

# 0.29.1

- Rapportpagina’s gebruiken de volledige beschikbare breedte en schalen mee op desktop, tablet en mobiel. Grafieken hebben geen vaste minimumbreedte meer.
- Nieuwe dividendkalender met maandnavigatie, weekdagen, betaalmarkeringen en een detailagenda. Ontvangen en geschatte betalingen hebben eigen kleuren; selecteer een dag voor de uitkeringen en basisdatum.
- Op kleine schermen blijven de kalenderdagen compact en verschijnen de bedragen en aandelen in de agenda eronder.

# 0.29.0

- Elk rapport heeft een eigen pagina-adres; het linkermenu toont alle tien rapporten zodra Rapporten wordt geopend.
- Dividendkalender toont betaaldatums en aandelen, ontvangen bedragen en toekomstige schattingen met instelbare jaarlijkse groei (standaard 3%).
- Schattingen gebruiken betalingen uit de afgelopen twaalf maanden voor nog open posities. De basisdatum blijft zichtbaar; toekomstige datums zijn indicatief en aangekondigde uitkeringen zijn niet gekoppeld.

# 0.28.0

- Professioneel rapportencentrum met tien analyses: overzicht, waardeontwikkeling, spreiding, winnaars en verliezers, resultaatopbouw, maanddividend, dividendbetalers, dividendkalender, sectoren en landen.
- Zeven interactieve grafiekvormen met details via muis en toetsenbord: donut, staaf, waterval, maandkolommen, lijn/oppervlak, resultaattegels en kalenderheatmap.
- Broker-, aandeel-, valuta-, jaar- en periodefilters, samenvattingskaarten en uitklapbare onderliggende cijfers. Valuta blijven gescheiden en ontbrekende gegevens worden overgeslagen.
- Waardehistorie wordt alleen bij openen van het rapport uit de lokale cache opgehaald; geen extra providerverzoeken of databaseschemaverandering.

# 0.27.1

- Rapporten slaan regels met ontbrekende koersen, bedragen of ongeldige gegevens over; geldige regels blijven berekend en zichtbaar.
- Toon het aantal overgeslagen regels en vermeld dat de totalen alleen de meegenomen regels bevatten. Bewaarde transacties blijven ongewijzigd.

# 0.27.0

- Vernieuwd rapportencentrum met portefeuille, resultaat per aandeel en dividend per maand of aandeel. Filters voor aandeel, valuta en dividendjaar binnen de gekozen broker.
- Actuele resultaten en jaarlijkse dividendcijfers blijven duidelijk gescheiden; valuta worden niet opgeteld.

## 0.26.2

- Onderaan het menu staat alleen de klikbare gebruikersnaam. Deze opent Mijn account met taalkeuze, account aanpassen en uitloggen.
- De gebruikerspagina werkt ook via het mobiele menu; accountwijzigingen blijven in een pop-up.

## 0.26.1

- Het accountmenu toont alleen de gebruikersnaam, zodat admin eenmaal verschijnt in plaats van admin · admin.

## 0.26.0

- Brokeraccount kiezen bovenaan Home, Aandelen en Dividend. Dezelfde keuze blijft actief bij het wisselen tussen pagina’s; Alle accounts toont het gezamenlijke overzicht.
- Aandelen, aantallen, waarde, winst, dividend, spreidingsgrafieken en categorievoortgang worden nu voor de gekozen brokeraccount berekend. Aandeeldetails volgen dezelfde selectie.
- Eerdere overzichten en lopende aanvragen worden bij een nieuwe brokerkeuze gewist of genegeerd, zodat gegevens van verschillende selecties niet worden gemengd.
- Nieuwe schermteksten beschikbaar in Nederlands, Engels en Spaans.

## 0.25.1

- Fondsen worden nu naast aandelen en ETF’s in de zoekresultaten getoond. Hierdoor kan Hybrid Index Fund NL-I worden toegevoegd door te zoeken op 0P0001IV37 en de gecontroleerde Yahoo-notering 0P0001IV37.F te kiezen.
- Zoekteksten verduidelijkt in Nederlands, Engels en Spaans. Valuta, notering, koers en historie blijven gecontroleerd via de bestaande koersdienst.

## 0.25.0 — 25 oktober 2026

- Nederlands, Engels en Spaans voor schermen, navigatie, formulieren, grafieken en meldingen.
- Bij de eerste start verschijnt een taalkeuze. Wijzig de taal later onder je account via Taal / Language / Idioma.
- De taal wordt per loginaccount opgeslagen en volgt het account op andere apparaten. Zonder aparte login geldt de opgeslagen voorkeur voor toegang via Home Assistant.
- Datums en bedragen volgen de gekozen taal. Eigen namen, notities, brontickers en gebruikersgegevens worden niet vertaald.
- Centrale vertaalcatalogus en automatische controle op ontbrekende talen bij nieuwe schermteksten.
- Databaseversie 18 voegt alleen een taalvoorkeur aan gebruikers toe, met vooraf een migratieback-up; bestaande portefeuillegegevens blijven behouden.

## 0.24.0

- Home Assistant kan de totale beleggingswaarde per oorspronkelijke valuta en het gezamenlijke totaal in euro ophalen via een aparte, alleen-lezen sensor-API.
- De sensorkoppeling is standaard uitgeschakeld. Een eigen toegangssleutel en optionele netwerkpoort beschermen de gegevens; het dashboard blijft via ingress bereikbaar.
- Instellingen toont actuele sensortotalen en passende REST-configuratie voor Home Assistant. Eén lokale aanvraag per minuut bedient alle sensoren vanuit de blijvende databasecache.
- Ontbrekende beurs- of wisselkoersen geven een onbekende waarde, met expliciete volledigheidsinformatie. Eurototalen gebruiken uitsluitend opgeslagen, gedateerde wisselkoersen; GBX wordt als pence omgerekend.
- De sensorwaarden zijn actuele beleggingswaarden over alle brokeraccounts; los brokersaldo en al uitgekeerd dividend worden niet nogmaals opgeteld. Databaseversie blijft 17.

## 0.23.0

- Home laadt uitsluitend opgeslagen portefeuillegegevens en wisselkoersen; externe koersaanvragen en ontbrekende historische valuta worden op de achtergrond bijgewerkt.
- Berekende overzichten worden gecomprimeerd in SQLite bewaard en in het geheugen hergebruikt, ook na een herstart. Revisies, appversie en dag voorkomen verouderde resultaten.
- Databaseversie 17 voegt een transactieve cache-revisie toe. Aankopen, dividend, koersen, historie, waarderingen, accounts, instellingen en FX-wijzigingen maken oude financiële overzichten ongeldig.
- De eerste paginarespons bevat de kerncijfers en totaalgrafieken; lange daghistorie wordt pas voor bekeken of vergeleken posities opgehaald, maximaal zes tegelijk.
- Verborgen rapporten en Home-tabellen worden niet bij iedere gegevensverversing opnieuw opgebouwd. Wisselen tussen valutakeuzes hergebruikt de reeds geladen euro-weergave.
- Historische wisselkoersen worden alleen voor ontbrekende perioden opgehaald; één nieuwe koers veroorzaakt geen nieuwe download van alle bekende koersjaren.
- Back-upherstel neemt geen berekende dashboardcaches over. Authenticatie blijft per aanvraag gecontroleerd; financiële gegevens en sessies worden niet in browseropslag bewaard.

## 0.22.2

- Trade Republic herkent CUSTOMER_INPAYMENT en geldbonussen zonder effecten als cashmutaties; ze tellen niet als aankoop of dividend.
- DELIVERY/MIGRATION wordt alleen overgeslagen bij een eenduidig gelijk uit-/inboekingspaar voor dezelfde ISIN, accountsoort, dag, valuta en prijs binnen één seconde. Onvolledige of afwijkende migraties blijven ter beoordeling.
- De bevestigde Netflix-splitsing van 17 november 2025 wordt gecontroleerd tegen het voorafgaande bezit en de 10-op-1-verhouding. Het bronbestand mag de extra aandelen of het nieuwe totaal bevatten; kostprijs, inleg en gerealiseerde winst blijven behouden.
- Een splitsing zonder geldvaluta gebruikt uitsluitend een eenduidige valuta uit dezelfde aankoophistorie of de opgeslagen ISIN-koppeling. Ontbrekende historie of een afwijkend aantal wordt niet geschat.
- Bestaande foutregels worden bij heropenen/opnieuw proberen opnieuw gecontroleerd met behoud van bron-ID’s, originele bronregels en handmatige beslissingen.

## 0.22.1

- Trade Republic: Private Markets-vooruitbetalingen zonder aantal/prijs worden als cashmutatie overgeslagen; de latere PRIVATE_FUND-aankoop gebruikt het expliciete aantal en de prijs.
- Apollo Global Private Markets ELTIF A2 UNH (LU3170240538) krijgt een eigen niet-beursgenoteerde ISIN-koppeling. Actuele fondswaardering is handmatig; er worden geen Yahoo-koersen of aankoophistorie als actuele waarde gebruikt.
- De boekdatum blijft behouden als de UTC-transactietijd op een aangrenzende dag valt. Beide bronvelden en bron-ID’s blijven ongewijzigd bewaard.
- Exacte, gecontroleerde EUR-noteringen toegevoegd voor Dividend 15 Split, BYD H, Rheinmetall, Xiaomi B en Alphabet A.
- Eerder afgewezen Trade Republic-regels worden bij heropenen of opnieuw proberen opnieuw gevalideerd met behoud van bronidentiteit en handmatige beslissingen. Herkende cashmutaties verdwijnen uit de openstaande beoordeling.
- Te beoordelen toont nu ook het Trade Republic-actietype en bronbedrag.
- Back-upherstel accepteert koppelingen van alle ondersteunde importaanbieders, inclusief Trade Republic, en blijft onbekende aanbieders weigeren.

## 0.22.0

- Imports krijgt een overzicht met brokerkaarten, duidelijke importstappen en een lege geschiedenis met uitleg. CSV-upload en API-rapportaanvraag openen in pop-ups.
- Nieuwe subpagina Imports → API-instellingen voor alle importaanbieders, met versleutelde Trading 212-verbindingen en uitleg over CSV bij Trade Republic.
- Trade Republic transactie-export CSV ondersteunt aankopen, verkopen en positief netto dividend voor aandelen en fondsen. Bron-ID’s, ISIN-koppelingen en ontdubbeling blijven per brokeraccount gescheiden.
- Onbekende acties, dividendcorrecties, ongeldige brongegevens en ontbrekende prijzen blijven duurzaam ter beoordeling; kostprijzen en corporate actions worden niet geschat.
- De beoordeling en heropening van importvoorbeelden gebruiken de adapter van de oorspronkelijke aanbieder.

## 0.21.2

- Alle pagina’s benutten de beschikbare schermbreedte; Home, Aandelen en Dividend hebben geen vaste maximumbreedte meer.
- Mobiele schermen krijgen passende kolommen, meeschalende velden en tabellen die binnen hun eigen paneel scrollen.
- Het zijmenu blijft ook op lage schermen volledig bereikbaar door te scrollen.

## 0.21.1

- Blijf 48 uur ingelogd; bij gebruik worden de sessie en cookie automatisch verlengd.
- Sessies blijven behouden na een appherstart en worden bij uitloggen, accountwijzigingen en herstel ingetrokken.
- Databaseversie 16 voegt blijvende sessies toe met uitsluitend gehashte sessiesleutels.

## 0.16.2

## 0.21.0
- Dividend krijgt Alle valuta’s in euro voor kerncijfers, grafieken, kalender, uitbetalers en betalingen. Historische bedragen worden op betaaldatum omgerekend; de verwachting houdt de huidige wisselkoers vast.
- Aandelen toont elke beursnotering één keer, met opgetelde aantallen en bedragen van alle brokers. Detailpagina’s openen altijd met alle brokertransacties.
- Sectoren, landen en beleggingstypen krijgen visuele verdelingen op basis van open beursnoteringen. Bedrijfslinks passen bij de huisstijl, met beurs en ticker onder de naam.
- De algemene brokerselector en dubbele kop verdwijnen op het aandelenoverzicht; de transactietabel onderaan is verwijderd. Aankopen toevoegen blijft beschikbaar via de pop-up.

## 0.20.0
- Dividendpagina toont alleen de eigen dashboardkop; algemene paginakop, brokerselector en koersstatus verdwijnen daar volledig.
- Home krijgt de optie Alle valuta’s in euro, met kerncijfers, totaalgrafiek, wegingen en posities in één overzicht.
- Aankoopinleg, verkopen en dividend worden op hun transactiedatum omgerekend; actuele marktwaarde tegen beschikbare actuele wisselkoersen. Britse pence worden correct verwerkt.
- Ontbrekende omrekeningen worden expliciet apart gehouden en historische wisselkoersen zo nodig opgehaald. Oorspronkelijke boekingen blijven intact.

## 0.19.0
- Nieuw dividenddashboard met kerncijfers per valuta, maandgrafiek, jaaroverzicht, kalender en grootste uitbetalers.
- Vooruitblik van 12 maanden, 3 jaar of 5 jaar op basis van de laatste twaalf maanden en huidige aantallen, met bekende splitsingen verwerkt.
- Verwachtingen zijn zichtbaar gescheiden van ontvangen betalingen, met uitleg over aannames en posities zonder bruikbare basis.
- Betalingen blijven filterbaar en sorteerbaar; dividend boeken blijft in een pop-up en grote overzichten laden betalingen in stappen.

## 0.18.0
- Dividend toont het cumulatieve percentage van de totale aankoopinleg sinds de eerste aankoop; groter bedrijfslogo.
- Bekende winst blijft zichtbaar bij ontbrekende koersen. Home noemt de betrokken aandelen direct, inclusief diagnostische Log-ID.
- Handmatige laatste koers per beursnotering (ook nul), met uitschakelen van automatische koers- en historieaanvragen en mogelijkheid tot hervatten.
- Databaseversie 15 bewaart laatste koersen, inclusief veilige migratie, back-up en herstel.

## 0.17.0
- Aandeelpagina met overzichtsblokken voor aantal, waarde in noteringsvaluta, eurowaarde en ontvangen dividend.
- Bedrijfslogo en korte bedrijfsomschrijving uit een bewaard bedrijfsprofiel, met rustige terugval als informatie ontbreekt.
- Teruglink en technische categorietoelichtingen verwijderd; eurowaarde gebruikt uitsluitend opgeslagen wisselkoersen van uiterlijk de koersdatum.

- Aandelencategorieën worden tijdens het aanvullen direct uit de opgeslagen metadata ververst, los van het gecachete portefeuilleoverzicht. Bij grote portefeuilles hoeft de lijst niet meer te wachten op de volledige koersronde.
- De aandelenpagina toont voortgang en onderscheidt nog ophalen, ophalen mislukt, ontbrekende brongegevens, handmatig leeggemaakte velden en de zelf te kiezen eigen categorie.
- Succesvolle aanvullingen maken de overzichtcache per aandeel ongeldig. De kleine metadata-aanvraag gebruikt geen koersdienst, herberekent geen historie en behoudt actieve kolomfilters en sortering.

## 0.16.1

- Profielaanvragen gebruiken het juiste antwoordformaat: HTML voor profielpagina’s en sessieopbouw, tekst voor de sessiecode en JSON voor de profiel-API. De aanvragen gebruiken ook een expliciete taalvoorkeur.
- HTTP 406 bij de directe profielaanvraag schakelt nu over naar de ingesloten API-respons op de profielpagina. Aanvraaglimieten (HTTP 429) blijven gerespecteerd.
- Foutlogs vermelden de precieze aanvraagstap, host, gevraagd formaat, HTTP-status en duur, zonder sessiegegevens of volledige antwoorden. Aanhoudende HTTP 406-fouten krijgen een gedeelde wachttijd om aanvraagpieken te voorkomen.

## 0.16.0

- Sector, land en type belegging worden eenmalig automatisch aangevuld via Yahoo Finance, ook voor bestaande aandelen. Profielen worden per ticker, beurs en valuta gecontroleerd en blijvend opgeslagen.
- Handmatige correcties winnen per veld, inclusief bewust leeg gemaakte velden. Bestaande categorieën uit 0.15.0 blijven behouden; de eigen categorie blijft handmatig.
- De detailpagina toont de API-status, ophaaldatum en ontbrekende gegevens. Verbindingsproblemen krijgen veilige diagnostische logs en een wachttijd voor opnieuw proberen; succesvolle profielen worden niet telkens opnieuw opgevraagd.
- Databaseversie 14 bewaart de voortgang en bescherming van handmatige categorieën, inclusief migratie, back-up en herstel.

## 0.15.0

- Open een aandeel vanuit de aandelenlijst voor een eigen detailpagina met koersgrafiek, periodekeuze en alle gekoppelde aankopen, verkopen, dividenden, splitsingen en kapitaalterugbetalingen. Gekoppelde openstaande importregels zijn herkenbaar als Te beoordelen.
- Sector, land, type belegging en een eigen categorie worden blijvend per beursnotering opgeslagen. Admins wijzigen deze in een pop-up; de indeling staat ook in de aandelenlijst en blijft behouden in back-ups.
- Klik op kolomkoppen om oplopend of aflopend te sorteren, ook in combinatie met kolomfilters. Home en Transacties sorteren en filteren vóór paginering.
- Databaseversie 13 voegt categorieën toe met automatische migratie en veiligheidsback-up; bestaande transacties en historie blijven behouden.

## 0.14.0

- Alle tabellen hebben combineerbare filters per kolom. Bij Home filteren deze vóór paginering; andere tabellen doorzoeken de geladen regels.
- Aantallen worden zonder wetenschappelijke nulnotatie getoond, met behoud van fractionele aandelen.
- Importlogs bevatten aantallen bronregels, aankopen, verkopen, duplicaten en te beoordelen regels. Afgewezen verkopen en splitsingen vermelden bezit, gevraagd aantal en verschil waar relevant.
- Bestaande transacties worden niet automatisch gewijzigd; ontbrekende historie en afgewezen regels blijven zichtbaar bij Te beoordelen.

# 0.13.1

- Foutieve importregels zonder geldige prijs of valuta worden niet meer aangeboden voor automatische beurskoppeling. De misleidende algemene TMX-aanvraagfout vervalt.
- AREB krijgt een exacte broker/ISIN-koppeling; historische TMX- en EPIX-transacties kunnen ook zonder actuele beursnotering gekoppeld worden. Deze koppelingen leveren geen fictieve koers op.
- Stock distribution en Custom stock distribution worden herkend als aandelenuitkering/omzetting en duurzaam apart gehouden voor controle van de over te dragen kostprijs. Automatisch boeken van fusies en CVR-rechten is nog niet ondersteund.
- Opgeslagen API-importvoorbeelden worden bij opnieuw openen bijgewerkt vanuit hun oorspronkelijke rapportregels, met behoud van bron-ID's en eerdere handmatige keuzes.
- GitHub publiceert na geslaagde controles automatisch de ontbrekende release voor de huidige appversie, met gevalideerde versie en changelogtekst. Commit, push en release zijn voortaan vaste projectafspraken.
- Lokale agentafspraken worden buiten de GitHub-repository gehouden.
- Databaseschema blijft 12.

# 0.13.0

- Home toont direct het portefeuilleoverzicht; de algemene paginakop, brokerselector en koersstatusbalk zijn daar verborgen. Het mobiele menu blijft bereikbaar.
- Transacties en aandelen aanpassen gebeurt in een modale pop-up, inclusief wijzigingshistorie en bestaande controles.
- Dezelfde pop-upstijl geldt voor aandelenkoppelingen, importbeoordelingen, gebruikers, dashboardinstellingen, API-verbindingen, nieuwe boekingen, brokeraccounts, beveiliging, herstellen en verwijderen.
- Pop-ups ondersteunen Sluiten/Annuleren, Escape en toetsenbordfocus; bij navigatie of afmelden sluiten ze.
- Vaste projectafspraak toegevoegd: toekomstige bewerkformulieren openen altijd in een pop-up.
- Appversie 0.13.0; databaseschema blijft 12.

# 0.12.0

- Nieuwe pagina Transacties: aankopen, verkopen, dividend, kapitaalterugbetalingen en splitsingen bekijken, zoeken en filteren per type/brokeraccount, met 50 regels per pagina.
- Admins kunnen datum, tijd, aantal, aankoop/verkooptype, prijs, ontvangen bedrag en dividendnotitie wijzigen waar van toepassing. De app controleert de volledige positiehistorie en weigert ongeldige verkopen of splitsingen.
- Originele importregels en bron-ID’s blijven behouden; correcties krijgen een blijvende wijzigingshistorie. Gelijktijdige wijzigingen worden niet overschreven.
- Instellingen biedt verwijderen van alle portefeuillegegevens of de administratie van één brokeraccount, inclusief bijbehorende imports en koppelingen. Vooraf verschijnt een overzicht en is de bevestiging VERWIJDEREN nodig.
- Vóór verwijderen wordt een volledige herstelback-up buiten de gewone back-uprotatie opgeslagen, met een downloadlink. Andere brokeraccounts, gebruikers, instellingen en API-verbindingen blijven behouden bij een gerichte verwijdering. Herimport van gewiste gegevens is mogelijk.
- Schema 12 voegt transaction_edits toe. Migratie en back-upherstel behouden de bestaande administratie; oudere back-ups blijven ondersteund.
- Het app-changelog (portfolio/CHANGELOG.md) is aangevuld met 0.11.0 en 0.12.0; voortaan worden het repository- en app-changelog bij iedere release samen bijgewerkt.

# 0.11.0

- Trading 212 herkent Return of capital manufactured payment automatisch als kapitaalterugbetaling. De ontvangst blijft in de bronvaluta en telt niet als dividendwinst.
- Stock split open past het volledige aantal aandelen aan met behoud van totale kostprijs, inleg en gerealiseerde winst. Stock split close controleert het oude aantal wanneer beide regels in hetzelfde bestand staan. Splitsingen zonder voorafgaand bezit blijven ter beoordeling staan.
- Bestaande afgewezen regels kunnen opnieuw worden geprobeerd; bronregels, eerdere handmatige keuzes en deduplicatie blijven behouden.
- Schema 11 voegt splitsingsmetadata toe. Migratie maakt vooraf een back-up; herstel ondersteunt oude en nieuwe back-ups.
- Versiegeschiedenis verplaatst uit README naar dit bestand. Voeg toekomstige wijzigingen hier bovenaan toe.

# 0.10.0

- Vernieuwd Home-dashboard met kerncijfers per valuta, grootste posities en beste/zwakste resultaten.
- Portefeuilletotaal als standaardgrafiek; gerichte vergelijking van maximaal zes posities.
- Lokaal doorzoekbare en sorteerbare positielijst met filters, wegingen en 25 regels per pagina.
- Responsieve grafiek zonder grote lege zijruimte, interactieve legenda en toetsenbordbediening.
- Dagwaardetabel pas opbouwen bij uitklappen, per 250 regels; geen extra providerverkeer voor dashboardfilters.
- Geen schemawijziging; schema blijft 10.

# 0.9.0

- Geldige importregels verwerken terwijl fouten duurzaam apart worden gehouden voor beoordeling.
- Admin-subpagina Te beoordelen met classificatie, opnieuw proberen en bewust overslaan; brondata en keuzes bewaren.
- Kapitaalterugbetalingen na expliciete keuze apart opslaan, zonder dividendwinst of automatische fiscale kostprijscorrectie.
- Savepoints per regel, idempotent opnieuw proberen en bescherming van eerder geboekte regels in gedeeltelijke imports.
- Madrid/OTC en gecontroleerde ISIN-koppelingen voor SAB, UNI en TCEHY.
- Schema 10 met automatische migratie-back-up en gevalideerd herstel van beoordelingen en kapitaalterugbetalingen.

# 0.8.0

- Admin-subpagina onder Imports voor blijvend opgeslagen en openstaande aandelenkoppelingen.
- Per brokeraccount, ISIN/bronticker en bronvaluta; bekende noteringen zonder nieuwe zoekaanvraag hergebruiken.
- Koersticker, beurs en valuta corrigeren met providercontrole; openstaande en volgende imports gebruiken de correctie, eerdere boekingen blijven behouden.
- Bestaande previewkoppelingen lokaal overnemen; register opnemen in back-up/herstel.
- Yahoo-aanvraaglimieten (429/503) laten koppelen pauzeren in plaats van alle instrumenten blijven proberen.
- Schema 9 met automatische veiligheidsback-up en transactionele migratie.

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

