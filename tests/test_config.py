def test_allowed_chat_ids_strips_whitespace(reload_config):
    config = reload_config(ALLOWED_CHAT_IDS="1, 2 ,3")

    assert config.ALLOWED == {"1", "2", "3"}
