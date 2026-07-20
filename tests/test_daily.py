import pytest

from core.daily import meals_for


@pytest.mark.parametrize("day_index,expected", [
    (0, ["bữa tối"]),               # Thứ Hai
    (1, ["bữa tối"]),               # Thứ Ba
    (2, ["bữa tối"]),               # Thứ Tư
    (3, ["bữa tối"]),               # Thứ Năm
    (4, ["bữa tối"]),               # Thứ Sáu
    (5, ["bữa trưa", "bữa tối"]),   # Thứ Bảy
    (6, ["bữa trưa", "bữa tối"]),   # Chủ Nhật
])
def test_meals_for(day_index, expected):
    assert meals_for(day_index) == expected
