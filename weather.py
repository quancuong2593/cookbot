import httpx
import config

URL = "https://api.open-meteo.com/v1/forecast"

async def _fetch(day_offset: int) -> str:
    params = {
        "latitude": config.LAT, "longitude": config.LON,
        "daily": ("temperature_2m_max,temperature_2m_min,"
                  "precipitation_probability_max,relative_humidity_2m_max"),
        "timezone": "Asia/Bangkok", "forecast_days": 2,
    }
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(URL, params=params)
        r.raise_for_status()
        d = r.json()["daily"]

    return (f"nhiệt độ {d['temperature_2m_min'][day_offset]}–{d['temperature_2m_max'][day_offset]}°C, "
            f"độ ẩm tối đa {d['relative_humidity_2m_max'][day_offset]}%, "
            f"khả năng mưa {d['precipitation_probability_max'][day_offset]}%")

async def get_today() -> str:
    """Lấy thời tiết hôm nay ở dạng câu mô tả ngắn cho prompt."""
    return await _fetch(0)

async def get_tomorrow() -> str:
    """Thời tiết ngày mai — dùng khi chuẩn bị gợi ý bữa sáng gửi tối hôm trước."""
    return await _fetch(1)
