import logging

import notifier


def test_setup_logging_no_file_handler_on_lambda(monkeypatch):
    """Tren Lambda, filesystem chi-doc — setup_logging() khong duoc tao FileHandler."""
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "cookbot-bot-prd")
    root = logging.getLogger()
    original_handlers = root.handlers[:]

    try:
        notifier.setup_logging()
        assert not any(isinstance(h, logging.FileHandler) for h in root.handlers)
    finally:
        for h in root.handlers[:]:
            root.removeHandler(h)
            h.close()
        for h in original_handlers:
            root.addHandler(h)
