"""ISIN listing hints from issuer exchange tables. Chart metadata is still validated.

Vanguard: fund-docs.vanguard.com factsheets 9679, 9503 and 9678.
Invesco/LSE: IE00BYVTMV98, EQGB on London Stock Exchange.
These are share-class identities, never fuzzy fund-name substitutions.
"""
CATALOGUE={
 'IE00BK5BQT80':['VWCE.AS','VWCE.DE','VWCE.MI','VWRA.L','VWRP.L'],
 'IE00B3XXRP09':['VUSA.AS','VUSA.DE','VUSA.MI','VUSA.L','VUSD.L'],
 'IE00BK5BR733':['VFEA.DE','VFEA.MI','VFEA.L'],
 'IE00BYVTMV98':['EQGB.L'],
}
