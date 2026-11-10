"""Pull sold eBay listings through Apify and add them to data/sales.jsonl.
Usage: python collector/run.py daily     (last couple of days; used by the schedule)
       python collector/run.py backfill  (last 90 days; run once at the start)"""
import json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text())
SALES = ROOT / "data" / "sales.jsonl"
KEEP = ["itemId", "title", "soldPrice", "soldPriceMax", "soldCurrency", "endedAt", "listingType",
        "isBestOfferAccepted", "url"]  # no seller details are stored


def load():
    if not SALES.exists(): return {}
    return {str(r["itemId"]): r for r in map(json.loads, filter(None, SALES.read_text().splitlines()))}


def save(sales):
    SALES.parent.mkdir(exist_ok=True)
    SALES.write_text("\n".join(json.dumps(v, separators=(",", ":")) for v in sales.values()) + "\n")


def main(mode):
    from apify_client import ApifyClient
    token = os.environ.get("APIFY_TOKEN")
    if not token: sys.exit("APIFY_TOKEN is not set. Add it as a GitHub secret (see README).")
    plan = CFG["backfill" if mode == "backfill" else "daily"]
    client, sales, spent, failures = ApifyClient(token), load(), 0.0, 0
    per_result = CFG["price_per_1000_results_usd"] / 1000
    print(f"Mode: {mode}. {len(sales)} sales on file. Budget ${CFG['max_budget_usd_per_run']}.")
    for q in CFG["queries"]:
        if spent + plan["count"] * per_result > CFG["max_budget_usd_per_run"]:
            print(f"Stopping before '{q}': the next search could exceed the budget."); break
        try:
            run = client.actor(CFG["actor"]).call(timeout_secs=1800, run_input={
                "keywords": [q], "ebaySite": CFG["ebay_site"], "daysToScrape": plan["days"], "count": plan["count"],
                "sortOrder": "endedRecently", "includeCompletedListings": True, "exactMatch": True})
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        except Exception as e:
            failures += 1; print(f"'{q}' failed: {e}"); continue
        spent += len(items) * per_result
        new = 0
        for it in items:
            iid = str(it.get("itemId") or "")
            if iid and iid not in sales:
                sales[iid] = {k: it.get(k) for k in KEEP}; new += 1
        save(sales)
        print(f"'{q}': {len(items)} results, {new} new. Estimated spend so far ${spent:.2f}")
    print(f"Done. {len(sales)} sales on file. Estimated spend ${spent:.2f}.")
    if failures == len(CFG["queries"]): sys.exit("Every search failed.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "daily")
