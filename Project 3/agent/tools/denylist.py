"""Files the agent must never read, list or search: secrets and private keys."""

import fnmatch
from pathlib import PurePosixPath

SECRET_NAME_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.secret",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
    "credentials",
    "credentials.*",
)


def is_secret_path(rel_path: str) -> bool:
    """True if the file's name looks like a secret. Only the file name is checked, not the folders."""
    name = PurePosixPath(rel_path.replace("\\", "/")).name.lower()
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in SECRET_NAME_PATTERNS)