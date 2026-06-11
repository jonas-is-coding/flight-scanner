"""Find affordable long-weekend flight deals with the Amadeus API."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

ORIGINS = ["DUS", "CGN", "DTM", "PAD"]
DESTINATIONS = ["IST", "SAW", "ATH", "NAP", "SKG"]
MAX_PRICE = 160.0
SEARCH_DAYS = 56
TRIP_LENGTH_DAYS = 3
OUT_FILE = Path("data/deals.json")
AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")


def get_token() -> str:
    """Request an OAuth token for the configured Amadeus application."""
    response = requests.post(
        f"{AMADEUS_BASE_URL}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["AMADEUS_CLIENT_ID"],
            "client_secret": os.environ["AMADEUS_CLIENT_SECRET"],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def search_flights(
    token: str,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
) -> list[dict[str, Any]]:
    """Search Amadeus flight offers for a single origin/destination/date pair."""
    response = requests.get(
        f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers",
        params={
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": 1,
            "currencyCode": "EUR",
            "max": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if response.status_code != 200:
        print(
            "Skipping failed search "
            f"{origin}->{destination} {departure_date}/{return_date}: "
            f"HTTP {response.status_code}"
        )
        return []

    return response.json().get("data", [])


def next_thursday_weekends(start: date) -> list[tuple[date, date]]:
    """Return Thursday-to-Sunday trips in the next eight weeks."""
    weekends = []

    for offset in range(1, SEARCH_DAYS + 1):
        departure = start + timedelta(days=offset)

        if departure.weekday() != 3:
            continue

        weekends.append((departure, departure + timedelta(days=TRIP_LENGTH_DAYS)))

    return weekends


def extract_deal(
    offer: dict[str, Any],
    origin: str,
    destination: str,
    departure: date,
    return_date: date,
) -> dict[str, Any] | None:
    """Convert an Amadeus offer into a compact website-friendly deal."""
    price = float(offer["price"]["grandTotal"])

    if price > MAX_PRICE:
        return None

    airlines = offer.get("validatingAirlineCodes", [])

    return {
        "origin": origin,
        "destination": destination,
        "departure": departure.isoformat(),
        "return": return_date.isoformat(),
        "price": price,
        "currency": offer.get("price", {}).get("currency", "EUR"),
        "airline": airlines[0] if airlines else "Unknown",
    }


def main() -> None:
    token = get_token()
    deals: list[dict[str, Any]] = []

    for departure, return_date in next_thursday_weekends(date.today()):
        for origin in ORIGINS:
            for destination in DESTINATIONS:
                offers = search_flights(
                    token,
                    origin,
                    destination,
                    departure.isoformat(),
                    return_date.isoformat(),
                )

                for offer in offers:
                    deal = extract_deal(offer, origin, destination, departure, return_date)
                    if deal is not None:
                        deals.append(deal)

    deals.sort(key=lambda deal: deal["price"])

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(deals, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Found {len(deals)} deals under {MAX_PRICE:.0f} EUR")


if __name__ == "__main__":
    main()
