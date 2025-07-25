# weather_api.py
"""
Получаем фактическую погоду в Торонто на текущий час
и нормализуем признаки под ML‑модель.
"""
import os, json, requests, datetime as dt, pytz, pandas as pd
from pathlib import Path

# ----------------------------------------------------------------------
def build_weather_row() -> pd.Series:
    api_key = os.getenv("WEATHER_API_KEY")          # Render → Environment
    if not api_key:
        raise RuntimeError("WEATHER_API_KEY not set")

    location = "Toronto"
    tz = pytz.timezone("America/Toronto")
    now = dt.datetime.now(tz).replace(minute=0, second=0, microsecond=0)

    url = (
        "https://api.weatherapi.com/v1/history.json"
        f"?key={api_key}&q={location}&dt={now:%Y-%m-%d}&aqi=no&alerts=no"
    )
    data = requests.get(url, timeout=30).json()

    # берём ровно тот час, что совпадает с now
    hour_block = next(
        h for h in data["forecast"]["forecastday"][0]["hour"]
        if dt.datetime.fromtimestamp(h["time_epoch"], tz) == now
    )

    df = pd.json_normalize(hour_block)[[
        "time", "temp_c", "dewpoint_c", "humidity",
        "wind_kph", "vis_km", "pressure_mb"
    ]]

    df["time"] = pd.to_datetime(df["time"])
    df["Month"] = df["time"].dt.month
    df["Day"]   = df["time"].dt.day
    df["Hour"]  = df["time"].dt.hour
    df.drop(columns=["time"], inplace=True)

    # порядок колонок задаёт твой JSON‑файл
    base_dir = Path(__file__).resolve().parent
    with open(base_dir / "columns.json") as f:
        cols = json.load(f)
    return df[cols].iloc[0]
# ----------------------------------------------------------------------

if __name__ == "__main__":
    print(build_weather_row())

