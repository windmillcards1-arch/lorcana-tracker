"""Pull sold eBay listings through Apify and add them to data/sales.jsonl.
Usage: python collector/run.py daily     (last couple of days; used by the schedule)
       python collector/run.py backfill  (last 90 days; run once at the start)"""
import json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text())
SALES = ROOT / "data" / "sales.jsonl"
KEEP = ["itemId", "title", "soldPrice", "soldPriceMax", "soldCurrency", "endedAt", "listingType",
        "isBestOfferAccepted", "url"]  # no seller details are stored


def field(obj, snake, camel):
    """Read a value from an Apify run result, whether the library returns an object or a dict."""
    return obj.get(camel) if isinstance(obj, dict) else getattr(obj, snake, None)


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
    client, sales, spent, failures, succeeded = ApifyClient(token), load(), 0.0, 0, 0
    per_result = CFG["price_per_1000_results_usd"] / 1000
    print(f"Mode: {mode}. {len(sales)} sales on file. Budget ${CFG['max_budget_usd_per_run']}.")
    for q in CFG["queries"]:
        if spent + plan["count"] * per_result > CFG["max_budget_usd_per_run"]:
            print(f"Stopping before '{q}': the next search could exceed the budget."); break
        try:
            run = client.actor(CFG["actor"]).call(run_input={
                "keywords": [q], "ebaySite": CFG["ebay_site"], "daysToScrape": plan["days"], "count": plan["count"],
                "sortOrder": "endedRecently", "includeCompletedListings": True, "exactMatch": True})
            status = str(field(run, "status", "status"))
            if "SUCCEEDED" not in status:
                raise RuntimeError(field(run, "status_message", "statusMessage") or status)
            items = list(client.dataset(field(run, "default_dataset_id", "defaultDatasetId")).iterate_items())
        except Exception as e:
            failures += 1; print(f"'{q}' failed: {e}")
            if "outage" in str(e).lower() or "unavailable" in str(e).lower():
                print("The scraper reports an outage. Stopping early; try again later."); break
            continue
        succeeded += 1
        spent += len(items) * per_result
        new = 0
        for it in items:
            iid = str(it.get("itemId") or "")
            if iid and iid not in sales:
                sales[iid] = {k: it.get(k) for k in KEEP}; new += 1
        save(sales)
        print(f"'{q}': {len(items)} results, {new} new. Estimated spend so far ${spent:.2f}")
    print(f"Done. {len(sales)} sales on file. Estimated spend ${spent:.2f}.")
    if succeeded == 0: sys.exit("No search succeeded.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "daily")
