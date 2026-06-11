# Flight Deal Radar

A small MVP that searches for affordable Thursday-to-Sunday weekend flights from NRW airports with the Amadeus Flight Offers Search API and displays them in a Next.js 16 application.

## What it checks

- Origins: `DUS`, `CGN`, `DTM`, `PAD`
- Destinations: `IST`, `SAW`, `ATH`, `NAP`, `SKG`
- Trip pattern: Thursday departure, Sunday return
- Search window: next 8 weeks
- Deal threshold: flights up to 160 EUR

## Required GitHub Secrets

Add these secrets to the repository before running the workflow:

- `AMADEUS_CLIENT_ID`
- `AMADEUS_CLIENT_SECRET`

## Run the flight scanner locally

```bash
python -m pip install -r requirements.txt
AMADEUS_CLIENT_ID=... AMADEUS_CLIENT_SECRET=... python src/check_flights.py
```

The scanner writes matching offers to `data/deals.json`.

## Run the Next.js app locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000` to view the deal radar. The Next.js app reads `data/deals.json` on the server and renders the current deal cards.
