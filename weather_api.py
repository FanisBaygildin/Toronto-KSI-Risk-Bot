# weather_api.py
"""
Getting the actual current hour weather in Toronto
"""
import os, json, requests, datetime as dt, pytz, pandas as pd, geohash2
from pathlib import Path


# --- CURRENT HOUR WEATHER pd.Series ----------------------------------------
def build_weather_row() -> pd.Series:
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("WEATHER_API_KEY Not Found")

    location = "Toronto"
    tz = pytz.timezone("America/Toronto")
    now = dt.datetime.now(tz).replace(minute=0, second=0, microsecond=0)    # current hour

    # 1) Making of parameters for weather request
    # no need: aqi — air quality; alerts
    params = {"key": api_key, "q": location, "days": 1, "aqi": "no", "alerts": "no"}
    data = requests.get("https://api.weatherapi.com/v1/forecast.json",
                        params=params,
                        timeout=30    # 30 sec to get an answer
                       ).json()
    
    # 2) Check for an error in JSON (even with 200 OK there can be an error)
    if "error" in data:
        raise RuntimeError(f"WeatherAPI error: {data['error']}")
    
    # 3) Check if nothing received
    forecastday = data.get("forecast", {}).get("forecastday", [])
    if not forecastday or not forecastday[0].get("hour"):
        raise RuntimeError("WeatherAPI: empty forecastday/hour for today")
    
    hours = forecastday[0]["hour"]    # list of forecast per hour for all 24 hrs of today
    
    # 4) Looking for the current hour in the list 'hours'
    try:
        hour_block = next(
            h for h in hours
            if dt.datetime.fromtimestamp(h["time_epoch"], tz).replace(minute=0, second=0, microsecond=0) == now
        )
    except StopIteration:
        # if the current hour is not found
        raise RuntimeError(f"WeatherAPI: no exact hour match for {now:%Y-%m-%d %H:00} in forecast")


    # convert a dict into a df
    df = pd.json_normalize(hour_block)[[
        "time", "temp_c", "dewpoint_c", "humidity", "wind_kph", "vis_km", "pressure_mb"
    ]]

    df["time"] = pd.to_datetime(df["time"])
    
    df["Month"] = df["time"].dt.month
    df["Day"] = df["time"].dt.day
    # df["weekday"] = df["time"].dt.weekday
    df["Hour"] = df["time"].dt.hour
    
    df.drop(columns=["time"], inplace=True)

    # columns order for the model
    base_dir = Path(__file__).resolve().parent
    with open(base_dir / "columns.json") as f:
        cols = json.load(f)
    return df[cols].iloc[0]    # using .iloc[0] to make it Series for the model
    
  
# ➊  DataFrame для ОДНОГО маршрута
#     geohashes : List[str]  (уже отсортированный список geohash5)
#     ➜ DataFrame с колонками:
#       Month, Day, temp_c, dewpoint_c, humidity,
#       wind_kph, vis_km, pressure_mb, Hour, Latitude, Longitude
# --- TEST DF -------------------------------------------------------------------
'''
Making a DF for a route with the same weather rows per each lat, lon pair of features
'''
def weather_df_for_route(geohashes) -> pd.DataFrame:
    # convert weather Series to Dict to add it for each geohash point
    base = build_weather_row().to_dict()

    rows = []
    for gh in geohashes:
        lat, lon = geohash2.decode(gh)
        rec = base.copy()
        rec["Latitude"]  = lat
        rec["Longitude"] = lon
        rows.append(rec)

    return pd.DataFrame(rows, columns=[
        "Month", "Day", "temp_c", "dewpoint_c", "humidity",
        "wind_kph", "vis_km", "pressure_mb", "Hour",
        "Latitude", "Longitude",
    ])

if __name__ == "__main__":
    print(build_weather_row())
    # # demo: создаём df для 3‑х geohash‑ов
    # print(weather_df_for_route(["f2m6p", "f2m6r", "f2m6v"]).head())
