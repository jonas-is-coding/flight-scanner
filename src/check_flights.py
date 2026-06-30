"""Find affordable long-weekend flight deals from public, keyless airline data.

The scanner intentionally sticks to public website endpoints that do not require
API keys. It currently checks Ryanair and Wizz Air, and it discovers Ryanair
routes dynamically so newly added destinations are picked up automatically.
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

# NRW airports plus nearby low-cost alternatives that are realistic for many NRW
# travellers. Providers silently skip airports/routes they do not serve.
ORIGINS = ["CGN", "NRN", "DUS", "DTM", "PAD", "FRA", "HHN", "EIN", "BRU", "CRL"]

# Fallback destination names for routes that cannot be discovered from an airline
# route index. Dynamic route discovery augments this list at runtime.
DESTINATIONS: dict[str, str] = {
    "BCN": "Barcelona",
    "AGP": "Málaga",
    "VLC": "Valencia",
    "PMI": "Palma de Mallorca",
    "ALC": "Alicante",
    "MAD": "Madrid",
    "SVQ": "Sevilla",
    "IBZ": "Ibiza",
    "ARN": "Stockholm",
    "CPH": "Kopenhagen",
    "GOT": "Göteborg",
    "LIS": "Lissabon",
    "OPO": "Porto",
    "FAO": "Faro",
    "NAP": "Neapel",
    "BLQ": "Bologna",
    "BRI": "Bari",
    "CTA": "Catania",
    "PMO": "Palermo",
    "BDS": "Brindisi",
    "ATH": "Athen",
    "SKG": "Thessaloniki",
    "CFU": "Korfu",
    "RHO": "Rhodos",
    "CHQ": "Chania (Kreta)",
    "BUD": "Budapest",
    "PRG": "Prag",
    "VIE": "Wien",
    "KRK": "Krakau",
    "WMI": "Warschau",
    "ZAD": "Zadar",
    "SPU": "Split",
    "DBV": "Dubrovnik",
    "TIA": "Tirana",
    "MLA": "Malta",
    "DUB": "Dublin",
    "BEG": "Belgrad",
    "SOF": "Sofia",
    "OTP": "Bukarest",
    "VAR": "Warna",
    "GDN": "Danzig",
    "KTW": "Kattowitz",
    "WRO": "Breslau",
    "CLJ": "Cluj-Napoca",
    "IAS": "Iași",
    "TSR": "Timișoara",
    "SKP": "Skopje",
    "KUT": "Kutaissi",
}

MAX_PRICE = 160.0
SEARCH_DAYS = 56
TRIP_LENGTH_DAYS = 3
OUT_FILE = Path("data/deals.json")

RYANAIR_AVAILABILITY_URL = "https://www.ryanair.com/api/booking/v4/de-de/availability"
RYANAIR_ROUTES_URL = "https://www.ryanair.com/api/views/locate/3/routes"
WIZZ_SEARCH_URL = "https://be.wizzair.com/27.24.0/Api/search/search"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

REQUEST_DELAY_SECONDS = 0.25


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    return session


def next_thursday_weekends(start: date) -> list[tuple[date, date]]:
    weekends = []
    for offset in range(1, SEARCH_DAYS + 1):
        departure = start + timedelta(days=offset)
        if departure.weekday() == 3:
            weekends.append((departure, departure + timedelta(days=TRIP_LENGTH_DAYS)))
    return weekends


def _cheapest_fare(flight: dict[str, Any]) -> float | None:
    fares = (flight.get("regularFare") or {}).get("fares", [])
    amounts = [fare["amount"] for fare in fares if isinstance(fare.get("amount"), (int, float))]
    return min(amounts) if amounts else None


def _cheapest_on_first_date(trip: dict[str, Any]) -> float | None:
    dates = trip.get("dates", [])
    if not dates:
        return None
    best: float | None = None
    for flight in dates[0].get("flights", []):
        if flight.get("faresLeft") == 0:
            continue
        amount = _cheapest_fare(flight)
        if amount is not None and (best is None or amount < best):
            best = amount
    return best


def load_ryanair_routes(session: requests.Session) -> dict[str, dict[str, str]]:
    """Return origin -> destination -> name for all public Ryanair routes.

    If the route index is unavailable, fall back to the maintained destination
    list so the scanner still works.
    """
    fallback = {origin: dict(DESTINATIONS) for origin in ORIGINS}
    try:
        response = session.get(RYANAIR_ROUTES_URL, timeout=30)
        response.raise_for_status()
        routes = response.json()
    except (requests.RequestException, ValueError) as error:
        print(f"Ryanair route discovery unavailable, using fallback routes: {error}")
        return fallback

    discovered: dict[str, dict[str, str]] = {origin: {} for origin in ORIGINS}
    for route in routes if isinstance(routes, list) else []:
        origin = route.get("airportFrom")
        destination = route.get("airportTo")
        if origin not in discovered or not isinstance(destination, str):
            continue
        name = route.get("cityTo") or route.get("airportToName") or DESTINATIONS.get(destination, destination)
        discovered[origin][destination] = str(name)

    for origin in ORIGINS:
        discovered[origin].update({k: v for k, v in DESTINATIONS.items() if k not in discovered[origin]})
    return discovered


def search_ryanair(session: requests.Session, origin: str, destination: str, departure: str, return_date: str) -> tuple[float, str] | None:
    params = {
        "ADT": 1,
        "TEEN": 0,
        "CHD": 0,
        "INF": 0,
        "Origin": origin,
        "Destination": destination,
        "DateOut": departure,
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
        response = session.get(RYANAIR_AVAILABILITY_URL, params=params, timeout=30)
    except requests.RequestException as error:
        print(f"Ryanair request failed {origin}->{destination} {departure}: {error}")
        return None
    if response.status_code != 200:
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
    return outbound + inbound, payload.get("currency", "EUR")


def _wizz_price(flight: dict[str, Any]) -> float | None:
    candidates = [flight.get("price"), flight.get("fare"), flight.get("basePrice")]
    for candidate in candidates:
        if isinstance(candidate, dict):
            amount = candidate.get("amount") or candidate.get("value")
            if isinstance(amount, (int, float)):
                return float(amount)
        if isinstance(candidate, (int, float)):
            return float(candidate)
    return None


def search_wizz(session: requests.Session, origin: str, destination: str, departure: str, return_date: str) -> tuple[float, str] | None:
    payload = {
        "flightList": [
            {"departureStation": origin, "arrivalStation": destination, "departureDate": departure},
            {"departureStation": destination, "arrivalStation": origin, "departureDate": return_date},
        ],
        "adultCount": 1,
        "childCount": 0,
        "infantCount": 0,
        "wdc": False,
    }
    try:
        response = session.post(WIZZ_SEARCH_URL, json=payload, timeout=30)
    except requests.RequestException as error:
        print(f"Wizz Air request failed {origin}->{destination} {departure}: {error}")
        return None
    if response.status_code != 200:
        return None
    try:
        data = response.json()
    except ValueError:
        return None

    flights = data.get("outboundFlights") or data.get("flightList") or []
    inbound = data.get("returnFlights") or []
    outbound_prices = [_wizz_price(f) for f in flights if isinstance(f, dict)]
    inbound_prices = [_wizz_price(f) for f in inbound if isinstance(f, dict)]
    outbound_prices = [p for p in outbound_prices if p is not None]
    inbound_prices = [p for p in inbound_prices if p is not None]
    if not outbound_prices or not inbound_prices:
        return None
    return min(outbound_prices) + min(inbound_prices), data.get("currencyCode", "EUR")


def append_deal(deals: list[dict[str, Any]], airline: str, origin: str, destination: str, departure: date, return_date: date, result: tuple[float, str] | None) -> None:
    if result is None:
        return
    price, currency = result
    if price > MAX_PRICE:
        return
    deals.append({
        "origin": origin,
        "destination": destination,
        "departure": departure.isoformat(),
        "return": return_date.isoformat(),
        "price": round(price, 2),
        "currency": currency,
        "airline": airline,
    })


def main() -> None:
    session = make_session()
    deals: list[dict[str, Any]] = []
    ryanair_routes = load_ryanair_routes(session)

    for departure, return_date in next_thursday_weekends(date.today()):
        departure_s = departure.isoformat()
        return_s = return_date.isoformat()
        for origin in ORIGINS:
            destinations = ryanair_routes.get(origin, DESTINATIONS)
            for destination in destinations:
                append_deal(deals, "Ryanair", origin, destination, departure, return_date, search_ryanair(session, origin, destination, departure_s, return_s))
                time.sleep(REQUEST_DELAY_SECONDS)
                append_deal(deals, "Wizz Air", origin, destination, departure, return_date, search_wizz(session, origin, destination, departure_s, return_s))
                time.sleep(REQUEST_DELAY_SECONDS)

    unique = {(d["airline"], d["origin"], d["destination"], d["departure"], d["return"], d["price"]): d for d in deals}
    deals = sorted(unique.values(), key=lambda deal: deal["price"])

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(deals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Found {len(deals)} deals under {MAX_PRICE:.0f} EUR")


if __name__ == "__main__":
    main()
