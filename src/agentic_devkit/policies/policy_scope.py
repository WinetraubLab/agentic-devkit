"""Hash the indexed files covered by a repository's policies."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

HASH_ALGORITHM = "sha256-policy-scope-configured-root-content-v6"


def _is_relative_folder(name: object) -> bool:
    return (
        isinstance(name, str) and bool(name) and name == name.strip()
        and not Path(name).is_absolute() and "\\" not in name
        and all(part not in {"", ".", "..", ".git"} for part in name.split("/"))
    )


def load_policy_scope(root: Path | str) -> tuple[str, ...]:
    """Read and validate repository-relative folders from policy/policy-scope-digest.json."""
    root = Path(os.path.abspath(root))
    config = root / "policy/policy-scope-digest.json"
    if config.is_symlink() or not config.is_file() or not config.resolve().is_relative_to(root.resolve()):
        raise ValueError("Create policy/policy-scope-digest.json with digests entries naming the reviewed root_folder values.")
    try:
        document = json.loads(config.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise ValueError("policy/policy-scope-digest.json must contain valid JSON.") from error
    if not isinstance(document, dict) or set(document) != {"digests"}:
        raise ValueError("policy/policy-scope-digest.json must contain only the digests field.")
    entries = document["digests"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("policy/policy-scope-digest.json digests must be a nonempty list.")
    scope = set()
    for entry in entries:
        if not isinstance(entry, dict) or "root_folder" not in entry or set(entry) - {"root_folder", "digest"}:
            raise ValueError("Each digests entry must name root_folder and may contain a generated digest.")
        name = entry["root_folder"]
        if not _is_relative_folder(name):
            raise ValueError(f"Invalid policy scope folder: {name!r}; use a repository-relative folder.")
        if name in scope:
            raise ValueError(f"Duplicate policy scope folder: {name}")
        scope.add(name)
        path = root / name
        if not path.is_dir() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Policy scope directory does not exist inside the repository: {name}")
    return tuple(sorted(scope))


def _hash_policy_roots(root: Path | str) -> dict[str, str]:
    root = Path(os.path.abspath(root))
    scope = load_policy_scope(root)
    digests = {}
    # Bind each folder's digest to the complete scope so removing a root also
    # invalidates reviews, without needing another stored metadata field.
    prefix = (HASH_ALGORITHM + "\0").encode()
    prefix += json.dumps(scope, ensure_ascii=False, separators=(",", ":")).encode() + b"\0"
    for folder in scope:
        target = (root / folder).resolve().relative_to(root.resolve()).as_posix()
        tracked = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(root), "ls-files", "--cached", "-z", "--", target],
            check=True, capture_output=True,
        ).stdout.decode("utf-8").split("\0")
        digest = hashlib.sha256(prefix)
        digest.update(folder.encode() + b"\0")
        if target != folder:
            digest.update(b"resolved-root\0" + target.encode() + b"\0")
        for name in sorted(filter(None, tracked), key=lambda name: name.encode("utf-16-be")):
            path = root / name
            if not path.exists():
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"Policy hashing does not allow symbolic links: {path}")
            if not path.is_file():
                continue
            content = path.read_bytes()
            digest.update(name.encode("utf-8") + b"\0")
            digest.update(str(len(content)).encode() + b"\0")
            digest.update(content + b"\0")
        digests[folder] = digest.hexdigest()
    return digests


def _scope_digest(digests: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(digests, sort_keys=True).encode()).hexdigest()


def hash_policy_scope(root: Path | str) -> str:
    """Summarize the current per-root digests without changing the JSON file."""
    return _scope_digest(_hash_policy_roots(root))
