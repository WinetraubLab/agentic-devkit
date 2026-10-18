"""Verify policy attestations against content digests and committed allowances."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess

from .policy_scope import _hash_policy_roots, _scope_digest
from .render_policy_documents import render_policy_documents

POLICY_SCOPE_DIGEST_FILE = "policy/policy-scope-digest.json"


@dataclass
class VerificationResult:
    baseline_revision: str
    digest: str
    policy_paths: list[Path]


def _list_markdown(directory: Path) -> list[Path]:
    paths = []
    for path in directory.iterdir():
        if path.is_symlink():
            raise ValueError(f"Policy verification does not allow symbolic links: {path}")
        if path.is_dir():
            paths.extend(_list_markdown(path))
        elif path.is_file() and path.suffix == ".md":
            paths.append(path)
    return sorted(paths)


def _read_attestation(
    markdown: str, *, baseline: bool = False,
) -> list[str] | None:
    headings = list(re.finditer(r"^# Attestation[ \t]*$", markdown, re.MULTILINE))
    if len(headings) != 1:
        return None
    body = markdown[headings[0].end():].strip()
    if baseline:
        body = re.sub(r"^Policy Scope Digest:\s*[a-f0-9]{64}\s*\n", "", body)
        body = re.sub(r"\nEvidence:[\s\S]*$", "", body)
    match = re.fullmatch(r"Noncompliant Files:[ \t]*([\s\S]*)", body)
    if not match:
        return None
    section = match[1].strip()
    if section == "NONE":
        return []
    if not section:
        return None
    paths = []
    for line in section.split("\n"):
        match = re.fullmatch(r"- ([^\s].*)", line)
        if not match:
            return None
        paths.append(match[1].strip())
    if len(set(paths)) != len(paths):
        return None
    return paths


def _read_stored_digest(root: Path) -> str | None:
    document = json.loads((root / POLICY_SCOPE_DIGEST_FILE).read_bytes())
    digests = {}
    for entry in document["digests"]:
        digest = entry.get("digest")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            return None
        digests[entry["root_folder"]] = digest
    return _scope_digest(digests)


def _write_stored_digest(root: Path, digests: dict[str, str]) -> None:
    document = {"digests": [
        {"root_folder": folder, "digest": digest}
        for folder, digest in sorted(digests.items())
    ]}
    (root / POLICY_SCOPE_DIGEST_FILE).write_bytes(
        (json.dumps(document, indent=2) + "\n").encode()
    )


def _read_at_revision(root: Path, revision: str, path: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path.relative_to(root).as_posix()}"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return result.stdout.decode("utf-8") if result.returncode == 0 else None


def _default_baseline() -> str:
    if os.environ.get("POLICY_BASE_REVISION"):
        return os.environ["POLICY_BASE_REVISION"]
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path:
        try:
            revision = json.loads(Path(event_path).read_bytes())["pull_request"]["base"]["sha"]
            if isinstance(revision, str) and revision:
                return revision
        except (OSError, ValueError, KeyError, TypeError):
            pass
    return "HEAD"


def _format_paths(paths: list[Path], root: Path) -> str:
    return "\n".join(f"- {path.relative_to(root).as_posix()}" for path in paths)


def verify_policy_attestations(
    *, root: Path | str | None = None, baseline_revision: str | None = None,
) -> VerificationResult:
    """Reset stale reviews and reject invalid or increased finding allowances."""
    root = Path(os.path.abspath(root or Path.cwd()))
    baseline_revision = baseline_revision if baseline_revision is not None else _default_baseline()
    directory = root / "policy"
    policies = sorted(
        path for field in directory.iterdir()
        if not field.is_symlink() and field.is_dir()
        for path in _list_markdown(field)
    )
    if not policies:
        raise ValueError("No Markdown policy files were found under policy/<field>/.")
    current_roots = _hash_policy_roots(root)
    current_digest = _scope_digest(current_roots)
    stored_digest = _read_stored_digest(root)
    if stored_digest != current_digest:
        render_policy_documents(root=root)
        _write_stored_digest(root, current_roots)
        raise ValueError(
            "Policy scope changed; all policy attestations were reset.\n"
            f"Stored policy scope digest: {stored_digest or 'missing or invalid'}\n"
            f"Current policy scope digest: {current_digest}\n\n"
            "This does not mean every listed policy has a violation. The verifier regenerated\n"
            "the policy documents with empty attestations because the configured review\n"
            "scope or its indexed files changed.\n\nPolicies requiring re-attestation:\n"
            f"{_format_paths(policies, root)}\n\n"
            "Review each listed policy, complete its Noncompliant Files attestation, "
            "and rerun agentic-devkit policy verify."
        )
    render_policy_documents(root=root, check=True)
    noncompliant = []
    for path in policies:
        current = _read_attestation(path.read_bytes().decode("utf-8"))
        baseline_markdown = _read_at_revision(root, baseline_revision, path)
        baseline = (
            _read_attestation(baseline_markdown, baseline=True)
            if baseline_markdown else None
        )
        allowance = len(baseline or [])
        if current is None or len(current) > allowance:
            noncompliant.append(path)
    if noncompliant:
        raise ValueError(
            "Policy attestation validation failed.\n"
            "The following policies have an incomplete or invalid attestation\n"
            "or more noncompliant files than the baseline allows:\n"
            f"{_format_paths(noncompliant, root)}\n\n"
            "Read each listed policy, correct its Noncompliant Files attestation, "
            "and rerun agentic-devkit policy verify."
        )
    return VerificationResult(baseline_revision, current_digest, policies)
