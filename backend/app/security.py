import base64
import hashlib
import logging
import re
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from .config import get_settings

SENSITIVE = re.compile(r"(?i)(authorization|access_token|refresh_token|client_secret|password)=([^\s&]+)")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        record.msg = SENSITIVE.sub(r"\1=<redacted>", message)
        record.args = ()
        return True


def safe_storage_path(path: str, allowed_root: Path) -> Path:
    candidate = Path(path).resolve()
    root = allowed_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path is outside managed storage")
    return candidate


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.token_encryption_key
    if not key:
        key_path = settings.storage_dir / ".token_key"
        if key_path.exists():
            key = key_path.read_text().strip()
        else:
            key = Fernet.generate_key().decode()
            key_path.write_text(key)
            try:
                key_path.chmod(0o600)
            except OSError:
                pass
    try:
        Fernet(key.encode())
    except Exception as exc:
        raise ValueError("TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc
    return Fernet(key.encode())


def encrypt_token(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ""


def decrypt_token(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored token cannot be decrypted; reconnect the account") from exc


def idempotency_digest(*parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode()).hexdigest()
