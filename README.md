# Lorcana graded spreads

A dashboard that shows which Lorcana cards have the biggest price gap between a PSA 10 and a BGS 9.5 or PCG 9.5,
built from eBay sold listings. It updates itself every day and lives at a link you can open anywhere.

**What's in this folder**
- `collector/` the code that fetches sales, reads grades and cards from listing titles, and calculates the gaps
- `docs/` the dashboard page (GitHub Pages serves this folder)
- `data/sales.jsonl` every sale collected so far (it starts with the 300 or so sales from your first test)
- `config.json` the searches, limits, and budget. Edit this to change what gets collected
- `github-workflow/daily.yml` the daily schedule (you'll paste this into GitHub in step 3)

You do not need your eBay developer keys for this version. The sold-price scraper replaces them.

## One-time setup (about 20 minutes)

**1. Create the repository.** Go to github.com/new. Name it `lorcana-tracker`, choose **Public**
(free GitHub accounts can only publish a Pages link from a public repo), and click **Create repository**.
Only sold-listing titles and prices are stored. Your keys never go in the repo.

**2. Upload the files.** Unzip this folder. On the new repo's page click **uploading an existing file**,
then drag in these items: `collector`, `data`, `docs`, `config.json`, `requirements.txt`, `README.md`.
Don't upload the `github-workflow` folder. Click **Commit changes**.

**3. Add the daily schedule.** In the repo click **Add file → Create new file**. In the name box type
`.github/workflows/daily.yml` (typing the slashes creates the folders). Open `github-workflow/daily.yml` from this
folder, copy everything, paste it into the big box, and click **Commit changes**.

**4. Save your Apify token as a secret.**
- In Apify: **Settings → API & integrations**, copy your Personal API token.
- In GitHub: your repo's **Settings → Secrets and variables → Actions → New repository secret**.
  Name it exactly `APIFY_TOKEN`, paste the token as the value, and save.
- Also check **Settings → Actions → General → Workflow permissions** is set to **Read and write permissions**.

**5. Turn on your link.** **Settings → Pages**. Under Source choose **Deploy from a branch**, pick branch `main`
and folder `/docs`, then **Save**. After a minute your dashboard is at
`https://YOUR-GITHUB-USERNAME.github.io/lorcana-tracker/`.

**6. Load the last 90 days.** Open the repo's **Actions** tab (click the green button if GitHub asks you to enable
workflows). Choose **Daily Lorcana update → Run workflow**, set `mode` to `backfill`, and run it. It can take
10 to 40 minutes. When the green check appears, refresh your dashboard link.

After that it runs by itself every morning and only collects the last 2 days.

## Cost

Apify charges per result (about $2.50 per 1,000 for this scraper, plus some platform usage you'll see on your Apify
billing page). `config.json` caps each run: the backfill stops before it passes `max_budget_usd_per_run` ($15), and a
daily run is at most 11 searches of 100 results, about $2.75 in the worst case and usually less. Check your Apify
bill after the first week and lower `count` or remove searches in `config.json` if you want it cheaper.

## Changing things

- **Which searches run:** edit `queries` in `config.json`.
- **How many sales count as enough:** the page has a "Minimum sales per grade" box; `min_sales_per_grade` sets the default.
- **The list length:** `top_n` (default 50).

## Known limits

- Cards are matched from listing titles (set, collector number, name). A few will be grouped or split wrongly.
- Lorcana graded sales are thin, so early on only a handful of cards have enough PSA 10 and BGS/PCG sales to compare.
  The list fills in as daily data accumulates.
- Raw (ungraded) prices come only from the `enchanted` and `iconic` searches, so they cover those cards first.
- eBay only shows about 90 days of sold history, so anything older exists only because this tool saved it.
