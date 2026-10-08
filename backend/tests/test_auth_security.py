from app.services.auth_security import hash_password, new_session_token, token_digest, verify_password


def test_password_round_trip():
    encoded = hash_password("safe-password-123")
    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password("safe-password-123", encoded)
    assert not verify_password("wrong-password", encoded)


def test_password_salts_are_unique():
    assert hash_password("same-password") != hash_password("same-password")


def test_legacy_demo_password_is_not_accepted():
    assert not verify_password("local-development", "local-development")


def test_sessions_use_unpredictable_tokens_and_hashes():
    first = new_session_token()
    second = new_session_token()
    assert first != second
    assert token_digest(first) != first
    assert token_digest(first) == token_digest(first)
