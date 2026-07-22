import pytest

from core.mealtime import current_meals


@pytest.mark.parametrize("day_index,hour,expected", [
    (1, 0, ["bữa tối"]),                      # Thứ Ba, 0h — bất kỳ giờ đều tối
    (1, 23, ["bữa tối"]),                     # Thứ Ba, 23h
    (5, 11, ["bữa trưa", "bữa tối"]),         # Thứ Bảy 11h59 -> hour=11, trước ranh giới
    (5, 12, ["bữa tối"]),                     # Thứ Bảy 12h01 -> hour=12, từ ranh giới
    (6, 8, ["bữa trưa", "bữa tối"]),          # Chủ Nhật 8h
])
def test_current_meals(day_index, hour, expected):
    assert current_meals(day_index, hour) == expected
