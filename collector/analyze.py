"""Turn data/sales.jsonl into docs/data/cards.json (for the dashboard) and docs/data/top50.csv."""
import csv, datetime as dt, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import analyze, rank

ROOT = pathlib.Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config.json").read_text())["analysis"]
sales_file = ROOT / "data" / "sales.jsonl"
sales = [json.loads(l) for l in sales_file.read_text().splitlines() if l.strip()] if sales_file.exists() else []
cards, meta = analyze(sales, cfg["window_days"])
out = ROOT / "docs" / "data"; out.mkdir(parents=True, exist_ok=True)
meta.update(updated=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), window_days=cfg["window_days"],
            min_sales=cfg["min_sales_per_grade"], top_n=cfg["top_n"], total_sales_on_file=len(sales))
(out / "cards.json").write_text(json.dumps({"meta": meta, "cards": cards}, separators=(",", ":")))
with open(out / "top50.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["rank", "card", "set", "number", "variant", "compared_with", "psa10_median", "psa10_sales",
                "other_median", "other_sales", "gap_usd", "gap_pct"])
    for i, (c, gap, other, o) in enumerate(rank(cards, cfg["min_sales_per_grade"], cfg["top_n"]), 1):
        p = c["g"]["PSA 10"]
        w.writerow([i, c["name"], c["set"], c["number"], c["variant"], other, p["med"], p["n"], o["med"], o["n"],
                    round(gap, 2), round(gap / o["med"] * 100, 1)])
print(f"{len(cards)} cards with graded sales; {meta['sales_used']} sales used, {meta['skipped']} skipped.")
print("Grades seen:", meta["grade_counts"])
