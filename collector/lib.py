"""Shared logic: read grades and cards out of eBay titles, then compute price stats."""
import datetime as dt, re, statistics
from collections import defaultdict

TARGET = ["RAW", "PSA 10", "BGS 9.5", "PCG 9.5"]

SETS = [("first chapter", "1"), ("rise of the floodborn", "2"), ("floodborn", "2"),
        ("into the inklands", "3"), ("inklands", "3"), ("ursula's return", "4"), ("ursulas return", "4"),
        ("shimmering skies", "5"), ("azurite sea", "6"), ("archazia", "7"), ("reign of jafar", "8"),
        ("jafar", "8"), ("fabled", "9"), ("whispers in the well", "10"), ("whispers", "10"),
        ("winterspell", "11"), ("wilds unknown", "12"), ("attack of the vine", "13"), ("hyperia city", "14")]
SET_LABEL = {"1": "The First Chapter", "2": "Rise of the Floodborn", "3": "Into the Inklands",
             "4": "Ursula's Return", "5": "Shimmering Skies", "6": "Azurite Sea", "7": "Archazia's Island",
             "8": "Reign of Jafar", "9": "Fabled", "10": "Whispers in the Well", "11": "Winterspell",
             "12": "Wilds Unknown", "13": "Attack of the Vine", "14": "Hyperia City"}

EXCLUDE = re.compile(r"\blots?\b|you pick|you choose|choose your|pick your|pick a\b|singles|set of\b|bundle|"
                     r"japanese|\bjp\b|\bjpn\b|chinese|korean|proxy|custom|\bsealed\b|booster|playmat|"
                     r"binder|sleeves|read desc|jumbo|oversize", re.I)
GRADE_RE = re.compile(r"\b(PSA|BGS|PCG|CGC|SGC|TAG|MPE|ACE)\s*#?\s*(?:GEM\s*MINT\s*)?(\d+(?:\.\d)?)")
GRADED_WORDS = re.compile(r"\b(GRADED|SLAB|PRISTINE|GEM MINT)\b")
STOP = set("""disney lorcana tcg card cards en english gem mint nm near rare legendary super epic common uncommon
foil cold holo enchanted iconic promo promos psa bgs pcg cgc sgc graded the of a an and in to for with
alt art quad beckett gen con pop new free ship shipping ja""".split())
for _name, _ in SETS:
    STOP.update(re.sub(r"[^a-z ]", "", _name).split())


def classify(title):
    """RAW, 'PSA 10', 'BGS 9.5', 'PCG 9.5', another grade label, or None to skip the listing."""
    if EXCLUDE.search(title):
        return None
    u = title.upper()
    found = set()
    for company, num in GRADE_RE.findall(u):
        v = float(num)
        if 1 <= v <= 10 and (v * 2) % 1 == 0:
            found.add(f"{company} {v:g}")
    if len(found) > 1:
        return None  # title names two grades; too ambiguous to trust
    if found:
        return found.pop()
    return "OTHER" if GRADED_WORDS.search(u) else "RAW"


def describe(title):
    u = title.upper()
    m = re.search(r"\bEN\s*-?\s*(P?\d{1,2}|C\d)\b", u)
    code = m.group(1) if m else None
    if not code:
        low = title.lower().replace("\u2019", "'")
        for name, c in SETS:
            if name in low:
                code = c
                break
    m = re.search(r"(\d{1,3})\s*/\s*\d{2,3}", u) or re.search(r"#\s*([0-9A-Z]{1,5})\b", u)
    number = m.group(1) if m else None
    if "ENCHANTED" in u: variant = "Enchanted"
    elif "ICONIC" in u: variant = "Iconic"
    elif re.search(r"PROMO|\bP\d\b|\bC1\b|D23", u) or (code and code[0] in "PC"): variant = "Promo"
    elif "FOIL" in u: variant = "Foil"
    else: variant = "Standard"
    words = [w for w in re.sub(r"[^A-Za-z ]", " ", title.replace("'", "")).lower().split()
             if w not in STOP and len(w) > 1]
    return code, number, variant, words


def _overlap(a, b):
    a, b = set(a), set(b)
    if not a or not b: return 0
    inter = len(a & b)
    if inter >= 2 and inter == min(len(a), len(b)): return 1
    return inter / len(a | b)


def build_groups(rows):
    """Group sales of the same card: by set + collector number when known, else by matching name words."""
    groups, by_key, pending = [], {}, []
    for r in rows:
        code, number, variant, words = describe(r["title"])
        r.update(_code=code, _num=number, _var=variant, _words=words)
        if code and number and code[0] not in "PC":
            g = by_key.setdefault((variant, code, number), None)
            if g is None:
                g = by_key[(variant, code, number)] = {"variant": variant, "code": code, "number": number,
                                                       "words": [], "rows": []}
                groups.append(g)
            g["rows"].append(r)
            if len(words) > len(g["words"]): g["words"] = words
        else:
            pending.append(r)
    for r in pending:
        best, score = None, 0.5
        for g in groups:
            if g["variant"] != r["_var"]: continue
            s = _overlap(g["words"], r["_words"])
            if s >= score: best, score = g, s
        if not best:
            best = {"variant": r["_var"], "code": r["_code"], "number": r["_num"], "words": r["_words"], "rows": []}
            groups.append(best)
        best["rows"].append(r)
        if len(r["_words"]) > len(best["words"]): best["words"] = r["_words"]
        best["code"] = best["code"] or r["_code"]
        best["number"] = best["number"] or r["_num"]
    return groups


def stats(rows):
    prices = [r["price"] for r in rows]
    rows = sorted(rows, key=lambda r: r["date"], reverse=True)
    kind = {"auction": "A", "best_offer_accepted": "BO"}
    return {"n": len(prices), "med": round(statistics.median(prices), 2), "min": min(prices), "max": max(prices),
            "last": rows[0]["date"],
            "sales": [[r["date"], r["price"], r["url"], kind.get(r["type"], "BIN")] for r in rows[:6]]}


def analyze(sales, window_days, today=None):
    today = today or dt.date.today()
    cutoff = today - dt.timedelta(days=window_days)
    rows, skipped, grade_counts = [], 0, defaultdict(int)
    for s in sales:
        try:
            price = float(s.get("soldPrice") or 0)
            date = dt.date.fromisoformat(str(s["endedAt"])[:10])
        except (ValueError, KeyError, TypeError):
            skipped += 1; continue
        cur = s.get("soldCurrency") or "USD"
        if price <= 0 or s.get("soldPriceMax") not in (None, "") or cur != "USD" or date < cutoff:
            skipped += 1; continue
        label = classify(s["title"])
        if label is None:
            skipped += 1; continue
        grade_counts[label] += 1
        if label in TARGET:
            rows.append({"title": s["title"], "price": price, "date": date.isoformat(), "grade": label,
                         "url": s.get("url") or "", "type": s.get("listingType") or ""})
    cards = []
    for g in build_groups(rows):
        by = defaultdict(list)
        for r in g["rows"]: by[r["grade"]].append(r)
        if not any(k != "RAW" for k in by): continue
        cards.append({"name": " ".join(w.capitalize() for w in g["words"]) or "Unidentified card",
                      "set": SET_LABEL.get(g["code"], g["code"] or ""), "number": g["number"] or "",
                      "variant": g["variant"], "g": {k: stats(v) for k, v in by.items()}})
    return cards, {"sales_used": len(rows), "skipped": skipped, "grade_counts": dict(grade_counts)}


def rank(cards, min_n, top_n):
    """Cards where PSA 10 sells for the most above BGS 9.5 or PCG 9.5 (whichever gap is wider)."""
    out = []
    for c in cards:
        psa = c["g"].get("PSA 10")
        if not psa or psa["n"] < min_n: continue
        best = None
        for other in ("BGS 9.5", "PCG 9.5"):
            o = c["g"].get(other)
            if o and o["n"] >= min_n:
                gap = psa["med"] - o["med"]
                if best is None or gap > best[1]: best = (c, gap, other, o)
        if best: out.append(best)
    out.sort(key=lambda t: t[1], reverse=True)
    return out[:top_n]
