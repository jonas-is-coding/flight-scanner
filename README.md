# Flight Deal Radar

A small MVP that searches for affordable Thursday-to-Sunday weekend flights from NRW airports with the Amadeus Flight Offers Search API.

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

## Run locally

```bash
python -m pip install -r requirements.txt
AMADEUS_CLIENT_ID=... AMADEUS_CLIENT_SECRET=... python src/check_flights.py
```

The script writes matching offers to `data/deals.json`. Serve the repository root with any static file server and open `web/index.html` to view the deal cards.
