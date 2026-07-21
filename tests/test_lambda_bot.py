import json
from unittest.mock import AsyncMock

import brain
import notifier
from runners import lambda_bot


def _event(update: dict, secret: str = "topsecret") -> dict:
    return {
        "headers": {"x-telegram-bot-api-secret-token": secret},
        "body": json.dumps(update),
    }


def _mock_io(monkeypatch):
    ask_mock = AsyncMock(return_value="Chào chị Như, hôm nay ăn canh chua nhé")
    send_mock = AsyncMock()
    send_log_mock = AsyncMock()
    monkeypatch.setattr(brain, "ask", ask_mock)
    monkeypatch.setattr(notifier, "send", send_mock)
    monkeypatch.setattr(notifier, "send_log", send_log_mock)
    return ask_mock, send_mock, send_log_mock


def test_lambda_bot_wrong_secret_returns_403(reload_config, monkeypatch):
    reload_config(WEBHOOK_SECRET="topsecret", ALLOWED_CHAT_IDS="111,222")
    ask_mock, send_mock, send_log_mock = _mock_io(monkeypatch)

    event = _event(
        {"message": {"chat": {"id": 111}, "text": "hôm nay ăn gì"}},
        secret="sai-secret",
    )
    result = lambda_bot.lambda_handler(event, None)

    assert result["statusCode"] == 403
    ask_mock.assert_not_called()
    send_mock.assert_not_called()
    send_log_mock.assert_not_called()


def test_lambda_bot_valid_message_returns_200(reload_config, monkeypatch):
    reload_config(WEBHOOK_SECRET="topsecret",
                  ALLOWED_CHAT_IDS="111,222", ADMIN_CHAT_ID="999")
    ask_mock, send_mock, send_log_mock = _mock_io(monkeypatch)

    event = _event({
        "message": {
            "chat": {"id": 111},
            "text": "hôm nay ăn gì",
            "from": {"first_name": "Như"},
        }
    })
    result = lambda_bot.lambda_handler(event, None)

    assert result["statusCode"] == 200
    ask_mock.assert_awaited_once_with("hôm nay ăn gì")
    send_mock.assert_awaited_once_with(
        "111", "Chào chị Như, hôm nay ăn canh chua nhé")
    send_log_mock.assert_awaited_once()


def test_lambda_bot_ignores_non_text_update_but_returns_200(
        reload_config, monkeypatch):
    reload_config(WEBHOOK_SECRET="topsecret", ALLOWED_CHAT_IDS="111,222")
    ask_mock, send_mock, send_log_mock = _mock_io(monkeypatch)

    # sticker: co "message" nhung khong co "text"
    event = _event({"message": {"chat": {"id": 111}, "sticker": {"file_id": "x"}}})
    result = lambda_bot.lambda_handler(event, None)

    assert result["statusCode"] == 200
    ask_mock.assert_not_called()
    send_mock.assert_not_called()
    send_log_mock.assert_not_called()


def test_lambda_bot_ignores_callback_query_but_returns_200(
        reload_config, monkeypatch):
    reload_config(WEBHOOK_SECRET="topsecret", ALLOWED_CHAT_IDS="111,222")
    ask_mock, send_mock, send_log_mock = _mock_io(monkeypatch)

    # callback_query: khong co key "message"
    event = _event({"callback_query": {"id": "1", "data": "chon_mon_1"}})
    result = lambda_bot.lambda_handler(event, None)

    assert result["statusCode"] == 200
    ask_mock.assert_not_called()
    send_mock.assert_not_called()
    send_log_mock.assert_not_called()
