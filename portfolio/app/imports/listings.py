"""ISIN listing hints from issuer exchange tables. Chart metadata is still validated.

Vanguard: fund-docs.vanguard.com factsheets 9679, 9503 and 9678.
Invesco/LSE: IE00BYVTMV98, EQGB on London Stock Exchange.
These are share-class identities, never fuzzy fund-name substitutions.
"""
CATALOGUE={
 # Exact share classes confirmed by Deutsche Börse; Yahoo metadata is validated.
 # live.deutsche-boerse.com/equity/{dividend-15-split-a-cd-15,byd-h,
 # xiaomi-corp-cl-b,alphabet-inc-class-a}; rheinmetall.com share/basic-information.
 'CA25537R1091':['641.F'],
 'CNE100000296':['BY6.F'],
 'DE0007030009':['RHM.DE'],
 'KYG9830T1067':['3CP.F'],
 'US02079K3059':['ABEA.DE','ABEA.F','GOOGL'],
 'US02919L8853':['AREB'],
 'CA29668H7085':['EPIX'],
 'NL0009272756':['TMX.AS'],
 'NL0009272749':['TDT.AS'],
 'ES0113860A34':['SAB.MC'],
 'ES0180907000':['UNI.MC'],
 'US88032Q1094':['TCEHY'],
 'US02209S1033':['MO'],
 'BE0003717312':['SOF.BR'],
 'IE00BK5BQT80':['VWCE.AS','VWCE.DE','VWCE.MI','VWRA.L','VWRP.L'],
 'IE00B3XXRP09':['VUSA.AS','VUSA.DE','VUSA.MI','VUSA.L','VUSD.L'],
 'IE00BK5BR733':['VFEA.DE','VFEA.MI','VFEA.L'],
 'IE00BYVTMV98':['EQGB.L'],
}

# Historical identities remain usable for the ledger after a delisting. These
# mappings do not assert that a current quote exists and never supply a price.
# Sources: VanEck product list / merger FAQ; Nasdaq ECA2025-551.
HISTORICAL_LISTINGS={
 'CA29668H7085':dict(symbol='EPIX',exchange='NASDAQ',currency='USD',name='ESSA Pharma Inc.',last_day='2025-10-09'),
 'NL0009272756':dict(symbol='TMX.AS',exchange='AMSTERDAM',currency='EUR',name='VanEck AMX UCITS ETF',last_day='2025-10-03'),
}

# Trading 212 instrument AREB.US identifies this exact share class on OTC.
# https://www.trading212.com/trading-instruments/invest/AREB.US
BROKER_LISTINGS={
 # Apollo's A2 UNH share class is an unlisted ELTIF, not a Yahoo ticker.
 # www.apollo.com/agpm-eltif ; source quantity/price remain the purchase basis.
 ('traderepublic','LU3170240538'):dict(symbol='LU3170240538',exchange='PRIVATE',currency='EUR',name='Apollo Global Private Markets ELTIF A2 UNH'),
 ('trading212','US02919L8853'):dict(symbol='AREB',exchange='OTC',currency='USD',name='American Rebel Holdings Inc.'),
}
