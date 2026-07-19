import httpx
import config

URL = "https://api.open-meteo.com/v1/forecast"

async def get_today() -> str:
    """Lấy thời tiết hôm nay ở dạng câu mô tả ngắn cho prompt."""
    params = {
        "latitude": config.LAT, "longitude": config.LON,
        "daily": ("temperature_2m_max,temperature_2m_min,"
                  "precipitation_probability_max,relative_humidity_2m_max"),
        "timezone": "Asia/Bangkok", "forecast_days": 1,
    }
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(URL, params=params)
        r.raise_for_status()
        d = r.json()["daily"]

    return (f"nhiệt độ {d['temperature_2m_min'][0]}–{d['temperature_2m_max'][0]}°C, "
            f"độ ẩm tối đa {d['relative_humidity_2m_max'][0]}%, "
            f"khả năng mưa {d['precipitation_probability_max'][0]}%")
