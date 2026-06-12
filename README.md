# Flight Deal Radar

A small MVP that searches for affordable Thursday-to-Sunday weekend flights from NRW airports by scraping Ryanair's public flight availability API and displays them in a Next.js 16 application.

## What it checks

- Origins: `CGN`, `NRN` (Weeze), `DUS`, `DTM`, `PAD`
- Destinations: many European leisure spots — Barcelona, Málaga, Valencia, Palma, Alicante, Madrid, Sevilla, Ibiza, Stockholm, Kopenhagen, Göteborg, Lissabon, Porto, Faro, Neapel, Bologna, Bari, Catania, Palermo, Brindisi, Athen, Thessaloniki, Korfu, Rhodos, Chania, Budapest, Prag, Wien, Krakau, Warschau, Zadar, Split, Dubrovnik, Tirana, Malta, Dublin
- Trip pattern: Thursday departure, Sunday return
- Search window: next 8 weeks
- Deal threshold: flights up to 160 EUR

## Data source

The scanner uses Ryanair's public, keyless availability endpoint (the same one
their website calls). **No API keys or GitHub Secrets are required** — the old
Amadeus integration has been removed.

Because the data comes from Ryanair only, the search is limited to Ryanair
routes. Destinations or airports that Ryanair doesn't serve simply return no
results (e.g. Istanbul is no longer covered). This setup is meant for private,
personal use.

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
