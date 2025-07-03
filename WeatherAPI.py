{
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": [],
      "mount_file_id": "1AVPMCTSL6T-LOk36adP6IoUwHYgrMBdc",
      "authorship_tag": "ABX9TyPTkZEkukjywNX7mj89iCHo",
      "include_colab_link": true
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "view-in-github",
        "colab_type": "text"
      },
      "source": [
        "<a href=\"https://colab.research.google.com/github/FanisBaygildin/Toronto-KSI-Risk-Bot/blob/main/WeatherAPI.py\" target=\"_parent\"><img src=\"https://colab.research.google.com/assets/colab-badge.svg\" alt=\"Open In Colab\"/></a>"
      ]
    },
    {
      "cell_type": "code",
      "source": [
        "import pandas as pd\n",
        "import numpy as np\n",
        "\n",
        "# for date/time\n",
        "from datetime import datetime, timezone, timedelta\n",
        "import datetime as dt\n",
        "\n",
        "import pytz\n",
        "# meteodata\n",
        "from astral.sun import sun\n",
        "from astral import LocationInfo\n",
        "import requests\n",
        "\n",
        "# for geohash\n",
        "import pygeohash as pgh\n",
        "\n",
        "import json\n",
        "import os\n",
        "\n",
        "\n",
        "def build_weather_df():\n",
        "    API_KEY = os.getenv(\"WEATHER_KEY\")\n",
        "    LOCATION = \"Toronto\"\n",
        "\n",
        "    tz = pytz.timezone(\"America/Toronto\")\n",
        "    now = dt.datetime.now(tz).replace(minute=0, second=0, microsecond=0)\n",
        "    today = now.date()\n",
        "\n",
        "    # На всякий случай берём и вчера, если текущий час — 00:00\n",
        "    dates_needed = {today}\n",
        "    if now.hour == 0:\n",
        "        dates_needed.add(today - dt.timedelta(days=1))\n",
        "\n",
        "    records = []\n",
        "\n",
        "    for date_ in dates_needed:\n",
        "        url = (\n",
        "            \"https://api.weatherapi.com/v1/history.json\"\n",
        "            f\"?key={API_KEY}&q={LOCATION}&dt={date_:%Y-%m-%d}&aqi=no&alerts=no\"\n",
        "        )\n",
        "        resp = requests.get(url, timeout=30)\n",
        "        resp.raise_for_status()\n",
        "        data = resp.json()\n",
        "\n",
        "        for hour in data[\"forecast\"][\"forecastday\"][0][\"hour\"]:\n",
        "            ts = dt.datetime.fromtimestamp(hour[\"time_epoch\"], tz)\n",
        "            if ts == now:\n",
        "                records.append(hour)\n",
        "\n",
        "    full_current_weather = pd.json_normalize(records)\n",
        "\n",
        "    full_current_weather = full_current_weather[['time', 'temp_c', 'dewpoint_c', 'humidity', 'wind_kph', 'vis_km', 'pressure_mb']]\n",
        "\n",
        "    # Преобразуем колонку DATE в datetime, если это ещё не сделано\n",
        "    full_current_weather['time'] = pd.to_datetime(full_current_weather['time'])\n",
        "\n",
        "    # Извлекаем месяц и день\n",
        "    full_current_weather['Month'] = full_current_weather['time'].dt.month\n",
        "    full_current_weather['Day'] = full_current_weather['time'].dt.day\n",
        "    full_current_weather['Hour'] = full_current_weather['time'].dt.hour\n",
        "\n",
        "    full_current_weather.drop('time', axis=1, inplace=True)\n",
        "\n",
        "    return full_current_weather"
      ],
      "metadata": {
        "id": "4BOtvokaxCGn"
      },
      "execution_count": null,
      "outputs": []
    }
  ]
}