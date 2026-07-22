from datetime import datetime
from zoneinfo import ZoneInfo

import config

TZ = ZoneInfo("Asia/Bangkok")


def current_meals(day_index: int, hour: int) -> list[str]:
    """0=Thứ Hai ... 6=Chủ Nhật. T2-T6 luôn bữa tối; T7/CN trước
    config.MEAL_BOUNDARY_HOUR là trưa+tối, từ giờ đó trở đi chỉ còn bữa tối."""
    if day_index < 5:
        return ["bữa tối"]
    if hour < config.MEAL_BOUNDARY_HOUR:
        return ["bữa trưa", "bữa tối"]
    return ["bữa tối"]


def current_meals_now() -> list[str]:
    now = datetime.now(TZ)
    return current_meals(now.weekday(), now.hour)
