# Flight Deal Radar

A small MVP that searches for affordable Thursday-to-Sunday weekend flights from NRW and nearby low-cost airports by querying public, keyless airline website endpoints and displays them in a Next.js 16 application.

## What it checks

- Origins: `CGN`, `NRN` (Weeze), `DUS`, `DTM`, `PAD` plus nearby alternatives `FRA`, `HHN`, `EIN`, `BRU`, `CRL`
- Providers: Ryanair and Wizz Air public, keyless website endpoints
- Destinations: a broad fallback set of European leisure spots, plus dynamically discovered Ryanair routes where available
- Trip pattern: Thursday departure, Sunday return
- Search window: next 8 weeks
- Deal threshold: flights up to 160 EUR

## Data source

The scanner uses public, keyless website endpoints from Ryanair and Wizz Air.
**No API keys or GitHub Secrets are required** — the old Amadeus integration has
been removed.

Ryanair routes are discovered dynamically from its public route index and merged
with a maintained fallback destination list. Destinations or airports that a
provider does not serve simply return no results. The scanner uses a normal
browser-like user agent and a small delay between requests so it remains suitable
for private, personal deal checks.

## Run the flight scanner locally

```bash
python -m pip install -r requirements.txt
python src/check_flights.py
```

The scanner writes matching offers to `data/deals.json`.

## Run the Next.js app locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000` to view the deal radar. The Next.js app reads `data/deals.json` on the server and renders the current deal cards.
