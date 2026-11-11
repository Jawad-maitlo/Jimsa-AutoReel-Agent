from pathlib import Path
import pytest
from app.config import get_settings
from app.security import decrypt_token, encrypt_token, idempotency_digest, safe_storage_path


def test_token_round_trip():
    token = "secret-token-value"
    encrypted = encrypt_token(token)
    assert encrypted != token
    assert token not in encrypted
    assert decrypt_token(encrypted) == token


def test_path_escape_rejected(tmp_path):
    with pytest.raises(ValueError):
        safe_storage_path(str(tmp_path / "outside.mp4"), get_settings().videos_dir)


def test_idempotency_stable_and_sensitive():
    assert idempotency_digest(1, 2, "a") == idempotency_digest(1, 2, "a")
    assert idempotency_digest(1, 2, "a") != idempotency_digest(1, 2, "b")
