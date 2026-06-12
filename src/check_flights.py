"""Find affordable long-weekend flight deals by scraping Ryanair's public API.

This replaces the previous Amadeus integration. Ryanair exposes a keyless JSON
availability endpoint (the same one their website uses), so no API credentials
or OAuth tokens are required anymore. We only query it for personal use.
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

# NRW airports. Ryanair mainly serves CGN and NRN (Weeze, marketed as
# "Düsseldorf Weeze"); the others rarely have Ryanair routes and will simply
# return no results.
ORIGINS = ["CGN", "NRN", "DUS", "DTM", "PAD"]

# Destination IATA code -> display name. Greatly expanded set of European
# leisure destinations that Ryanair flies to from NRW.
DESTINATIONS: dict[str, str] = {
    # Spain
    "BCN": "Barcelona",
    "AGP": "Málaga",
    "VLC": "Valencia",
    "PMI": "Palma de Mallorca",
    "ALC": "Alicante",
    "MAD": "Madrid",
    "SVQ": "Sevilla",
    "IBZ": "Ibiza",
    # Scandinavia
    "ARN": "Stockholm",
    "CPH": "Kopenhagen",
    "GOT": "Göteborg",
    # Portugal
    "LIS": "Lissabon",
    "OPO": "Porto",
    "FAO": "Faro",
    # Italy
    "NAP": "Neapel",
    "BLQ": "Bologna",
    "BRI": "Bari",
    "CTA": "Catania",
    "PMO": "Palermo",
    "BDS": "Brindisi",
    # Greece
    "ATH": "Athen",
    "SKG": "Thessaloniki",
    "CFU": "Korfu",
    "RHO": "Rhodos",
    "CHQ": "Chania (Kreta)",
    # Central & Eastern Europe
    "BUD": "Budapest",
    "PRG": "Prag",
    "VIE": "Wien",
    "KRK": "Krakau",
    "WMI": "Warschau",
    # Adriatic & Balkans
    "ZAD": "Zadar",
    "SPU": "Split",
    "DBV": "Dubrovnik",
    "TIA": "Tirana",
    # Islands & misc
    "MLA": "Malta",
    "DUB": "Dublin",
}

MAX_PRICE = 160.0
SEARCH_DAYS = 56
TRIP_LENGTH_DAYS = 3
OUT_FILE = Path("data/deals.json")

# Ryanair availability endpoint (same one the website calls). The "de-de"
# market makes it return EUR prices, which is what we want for German origins.
AVAILABILITY_URL = "https://www.ryanair.com/api/booking/v4/de-de/availability"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Referer": "https://www.ryanair.com/",
}

# Be polite: small pause between requests so we don't hammer the endpoint.
REQUEST_DELAY_SECONDS = 0.25


def make_session() -> requests.Session:
    """Create a session and warm it up so Ryanair hands us cookies."""
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    try:
        session.get("https://www.ryanair.com/de/de", timeout=30)
    except requests.RequestException:
        # A failed warmup is not fatal; the availability call may still work.
        pass
    return session


def next_thursday_weekends(start: date) -> list[tuple[date, date]]:
    """Return Thursday-to-Sunday trips in the next eight weeks."""
    weekends = []

    for offset in range(1, SEARCH_DAYS + 1):
        departure = start + timedelta(days=offset)

        if departure.weekday() != 3:
            continue

        weekends.append((departure, departure + timedelta(days=TRIP_LENGTH_DAYS)))

    return weekends


def _cheapest_fare(flight: dict[str, Any]) -> float | None:
    """Return the lowest published fare amount for a single flight, if any."""
    fares = (flight.get("regularFare") or {}).get("fares", [])
    amounts = [
        fare["amount"]
        for fare in fares
        if isinstance(fare.get("amount"), (int, float))
    ]
    return min(amounts) if amounts else None


def _cheapest_on_first_date(trip: dict[str, Any]) -> float | None:
    """Cheapest fare on a trip's first (and, with flex=0, only) date."""
    dates = trip.get("dates", [])
    if not dates:
        return None

    best: float | None = None
    for flight in dates[0].get("flights", []):
        # Skip sold-out flights with no seats left.
        if flight.get("faresLeft") == 0:
            continue
        amount = _cheapest_fare(flight)
        if amount is None:
            continue
        if best is None or amount < best:
            best = amount

    return best


def search_round_trip(
    session: requests.Session,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
) -> tuple[float, str] | None:
    """Search Ryanair for a Thu->Sun round trip.

    Returns (total_price, currency) for the cheapest outbound + inbound
    combination, or None if nothing is available.
    """
    params = {
        "ADT": 1,
        "TEEN": 0,
        "CHD": 0,
        "INF": 0,
        "Origin": origin,
        "Destination": destination,
        "DateOut": departure_date,
        "DateIn": return_date,
        "FlexDaysBeforeOut": 0,
        "FlexDaysOut": 0,
        "FlexDaysBeforeIn": 0,
        "FlexDaysIn": 0,
        "RoundTrip": "true",
        "ToUs": "AGREED",
        "IncludeConnectingFlights": "false",
    }

    try:
        response = session.get(AVAILABILITY_URL, params=params, timeout=30)
    except requests.RequestException as error:
        print(f"Request failed {origin}->{destination} {departure_date}: {error}")
        return None

    if response.status_code != 200:
        # 404/4xx usually just means Ryanair does not fly this route.
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    trips = payload.get("trips", [])
    if len(trips) < 2:
        return None

    outbound = _cheapest_on_first_date(trips[0])
    inbound = _cheapest_on_first_date(trips[1])

    if outbound is None or inbound is None:
        return None

    currency = payload.get("currency", "EUR")
    return outbound + inbound, currency


def main() -> None:
    session = make_session()
    deals: list[dict[str, Any]] = []

    for departure, return_date in next_thursday_weekends(date.today()):
        for origin in ORIGINS:
            for destination in DESTINATIONS:
                result = search_round_trip(
                    session,
                    origin,
                    destination,
                    departure.isoformat(),
                    return_date.isoformat(),
                )
                time.sleep(REQUEST_DELAY_SECONDS)

                if result is None:
                    continue

                price, currency = result
                if price > MAX_PRICE:
                    continue

                deals.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "departure": departure.isoformat(),
                        "return": return_date.isoformat(),
                        "price": round(price, 2),
                        "currency": currency,
                        "airline": "Ryanair",
                    }
                )

    deals.sort(key=lambda deal: deal["price"])

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(deals, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Found {len(deals)} deals under {MAX_PRICE:.0f} EUR")


if __name__ == "__main__":
    main()
