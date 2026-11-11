"""Linear-time indexes for the periodic market refresh.

Derived only from the current snapshot. Does not change stored transactions.
"""

def purchase_index(purchases):
    """Return earliest purchase date and transferred sells by instrument."""
    earliest = {}
    transferred_sells = set()
    for row in purchases:
        instrument = (row["symbol"], row["exchange"], row["currency"])
        date = row.get("purchased_on")
        if date and (instrument not in earliest or date < earliest[instrument]):
            earliest[instrument] = date
        if row.get("transfer_id") and row.get("side") == "SELL":
            transferred_sells.add(instrument)
    return earliest, transferred_sells
