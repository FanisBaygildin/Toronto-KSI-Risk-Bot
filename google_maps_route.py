# google_maps_route.py
import os
import httpx
from typing import List, Dict

BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"
API_KEY = os.getenv("GMAPS_API_KEY")        # читаем при импорте

async def get_routes(
    origin_pc: str,
    dest_pc: str,
    max_routes: int = 3,
) -> List[Dict[str, str]]:
    """
    Возвращает до `max_routes` маршрутов вида:
    [{'distance_km': 12.4, 'duration_text': '18 mins'}, ...]
    """
    if not API_KEY:
        raise RuntimeError("GMAPS_API_KEY env var not set!")

    params = {
        "origin": origin_pc,
        "destination": dest_pc,
        "alternatives": "true",   # просим несколько вариантов
        "units": "metric",
        "key": API_KEY,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "OK":
        raise RuntimeError(f"Directions API error: {data.get('status')}: {data.get('error_message')}")

    routes = []
    for route in data["routes"][:max_routes]:
        leg = route["legs"][0]
        routes.append(
            {
                "distance_km": round(leg["distance"]["value"] / 1000, 1),
                "duration_text": leg["duration"]["text"],
            }
        )
    return routes
