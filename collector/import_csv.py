"""Add rows from an Apify CSV export to data/sales.jsonl.  Usage: python collector/import_csv.py file.csv"""
import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from run import KEEP, load, save

sales, added = load(), 0
for row in csv.DictReader(open(sys.argv[1], newline="", encoding="utf-8")):
    iid = row.get("itemId")
    if not iid or iid in sales: continue
    rec = {k: (row.get(k) or None) for k in KEEP}
    for k in ("soldPrice", "soldPriceMax"):
        rec[k] = float(rec[k]) if rec[k] else None
    sales[iid] = rec; added += 1
save(sales); print(f"Added {added}; {len(sales)} sales on file.")
