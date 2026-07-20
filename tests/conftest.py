import importlib
import os

import pytest

# Set truoc khi bat ky test module nao import config (qua core.*) —
# dam bao test khong bao gio phu thuoc vao .env that tren may dev.
os.environ.setdefault("TELEGRAM_TOKEN", "123456:test-telegram-token")
os.environ.setdefault("LOG_BOT_TOKEN", "123456:test-log-token")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("ALLOWED_CHAT_IDS", "111,222")
os.environ.setdefault("ADMIN_CHAT_ID", "999")


@pytest.fixture
def reload_config(monkeypatch):
    """Set env roi reload config module, tra ve config voi gia tri moi.

    core/handler.py va core/daily.py giu tham chieu toi module `config`
    (khong phai tung ten rieng le), nen reload lam thay doi module object
    trong sys.modules va duoc thay ngay lap tuc o moi noi da import config.
    """
    def _reload(**env_overrides):
        for key, value in env_overrides.items():
            monkeypatch.setenv(key, value)
        import config
        importlib.reload(config)
        return config

    yield _reload

    import config
    importlib.reload(config)
