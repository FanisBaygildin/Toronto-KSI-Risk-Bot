# google_maps_route.py
import os, httpx, polyline, geohash2 as geohash
from typing import List, Dict

BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"
STATIC_URL = "https://maps.googleapis.com/maps/api/staticmap"
API_KEY = os.getenv("GMAPS_API_KEY")

async def get_routes(origin_pc: str,
                     dest_pc: str,
                     max_routes: int = 3
                     ) -> List[Dict[str, str]]:
    """Returns list of routes + polyline"""
    if not API_KEY:
        raise RuntimeError("GMAPS_API_KEY env var not set!")

    params = {
        "origin": origin_pc,
        "destination": dest_pc,
        "alternatives": "true",
        "units": "metric",
        "key": API_KEY,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        data = (await client.get(BASE_URL, params=params)).json()

    if data.get("status") != "OK":
        raise RuntimeError(f"Directions API error: {data.get('status')}")

    routes = []
    for r in data["routes"][:max_routes]:
        leg = r["legs"][0]
        poly = r["overview_polyline"]["points"]

        # --- geohash‑5 -------------------------------------------------
        points = polyline.decode(poly)           # [(lat, lon), …]
        # берём каждую 5‑ю точку, чтобы не плодить тысячи ячеек
        hashes = sorted({geohash.encode(lat, lon, precision=5)
                         for lat, lon in points[::5]})

        routes.append(
            {
                "distance_km":  round(leg["distance"]["value"] / 1000, 1),
                "duration_text": leg["duration"]["text"],
                "poly":          poly,
                "geohash5":      hashes,
            }
        )
    return routes


async def static_map(origin_pc: str,
                     dest_pc: str,
                     polylines: List[str],
                     size: str = "640x400") -> bytes:
    """PNG-map with routes"""
    colors = ["0xFF0000FF", "0x00AA00FF", "0x0000FFFF"]  # Red, Green, Blue
    parts = [
        f"size={size}",
        f"markers=label:S|{origin_pc}",
        f"markers=label:D|{dest_pc}",
    ]
    for i, poly in enumerate(polylines):
        parts.append(f"path=color:{colors[i]}|weight:5|enc:{poly}")
    parts.append(f"key={API_KEY}")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{STATIC_URL}?{'&'.join(parts)}")
        resp.raise_for_status()
        return resp.content
