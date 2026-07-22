from pathlib import Path
from unittest.mock import AsyncMock

import pytest

import brain
import weather
import core.mealtime as mealtime
from core import handler

HANDLER_SOURCE = Path(handler.__file__).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_handle_message_blocks_non_whitelisted_chat_id(
        reload_config, monkeypatch):
    reload_config(ALLOWED_CHAT_IDS="111,222")
    ask_mock = AsyncMock()
    monkeypatch.setattr(brain, "ask", ask_mock)
    notify_admin = AsyncMock()

    result = await handler.handle_message("999", "xin chào", notify_admin)

    assert result is None
    ask_mock.assert_not_called()
    notify_admin.assert_awaited_once()
    assert "999" in notify_admin.await_args.args[0]


@pytest.mark.asyncio
async def test_handle_message_calls_brain_ask_for_allowed_chat_id(
        reload_config, monkeypatch):
    reload_config(ALLOWED_CHAT_IDS="111,222")
    ask_mock = AsyncMock(return_value="Chào chị Như, hôm nay ăn canh chua nhé")
    monkeypatch.setattr(brain, "ask", ask_mock)
    monkeypatch.setattr(weather, "get_today", AsyncMock(return_value="nắng nhẹ"))
    monkeypatch.setattr(mealtime, "current_meals_now", lambda: ["bữa tối"])
    notify_admin = AsyncMock()

    result = await handler.handle_message("111", "hôm nay ăn gì", notify_admin)

    ask_mock.assert_awaited_once_with("hôm nay ăn gì", "nắng nhẹ", ["bữa tối"])
    assert result == "Chào chị Như, hôm nay ăn canh chua nhé"
    # mirror log la viec cua runner, core khong tu goi notify_admin khi hop le
    notify_admin.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_degrades_gracefully_when_weather_fails(
        reload_config, monkeypatch):
    reload_config(ALLOWED_CHAT_IDS="111,222")
    ask_mock = AsyncMock(return_value="Cứ ăn nhẹ bụng thôi chị Như nhé")
    monkeypatch.setattr(brain, "ask", ask_mock)
    monkeypatch.setattr(weather, "get_today", AsyncMock(side_effect=RuntimeError("sập")))
    monkeypatch.setattr(mealtime, "current_meals_now", lambda: ["bữa tối"])
    notify_admin = AsyncMock()

    result = await handler.handle_message("111", "hôm nay ăn gì", notify_admin)

    # weather that bai khong duoc lam bot im lang — van goi brain.ask, chi thieu weather
    ask_mock.assert_awaited_once_with("hôm nay ăn gì", None, ["bữa tối"])
    assert result == "Cứ ăn nhẹ bụng thôi chị Như nhé"


def test_core_handler_does_not_import_notifier():
    """Architecture test — chan ai do vo tinh import lai notifier vao core/."""
    assert "notifier" not in HANDLER_SOURCE
