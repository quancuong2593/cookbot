import pytest

from core.daily import meals_for


@pytest.mark.parametrize("day_index,slot,expected", [
    (0, "morning", ["bữa tối"]),                # Thứ Hai 9h
    (1, "morning", ["bữa tối"]),                # Thứ Ba 9h
    (2, "morning", ["bữa tối"]),                # Thứ Tư 9h
    (3, "morning", ["bữa tối"]),                # Thứ Năm 9h
    (4, "morning", ["bữa tối"]),                # Thứ Sáu 9h
    (4, "evening", ["bữa sáng thứ Bảy"]),        # Thứ Sáu 21h
    (5, "morning", ["bữa trưa", "bữa tối"]),     # Thứ Bảy 9h
    (5, "evening", ["bữa sáng Chủ nhật"]),       # Thứ Bảy 21h
    (6, "morning", ["bữa trưa", "bữa tối"]),     # Chủ Nhật 9h
])
def test_meals_for(day_index, slot, expected):
    assert meals_for(day_index, slot) == expected
