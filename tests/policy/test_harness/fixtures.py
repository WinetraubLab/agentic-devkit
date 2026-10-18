"""Provide isolated Git repositories and CLI calls for policy tooling tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from agentic_devkit.policies.policy_scope import _hash_policy_roots
from agentic_devkit.policies.verify_policy_attestations import _write_stored_digest
from agentic_devkit.policies.render_policy_documents import render_policy_documents

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments], check=True, capture_output=True, text=True,
    ).stdout


def _commit(root: Path, message: str = "Record baseline") -> None:
    _git(root, "add", ".")
    _git(root, "-c", "user.name=Policy Test", "-c", "user.email=policy-test@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", message)


def _complete(path: Path, files: list[str] | None = None) -> None:
    section = "\n" + "\n".join(f"- {file}" for file in files) if files else " NONE"
    path.write_text(re.sub(r"^Noncompliant Files:[\s\S]*$", "Noncompliant Files:" + section,
                           path.read_text(), flags=re.MULTILINE))


def _renderer_fixture(
    case: unittest.TestCase, *, policy_source: str | None = None,
) -> Path:
    temporary = tempfile.TemporaryDirectory(prefix="devkit-policy-test-")
    case.addCleanup(temporary.cleanup)
    root = Path(temporary.name)
    for name in ("src", "actions/data-types", "actions/technical-skills/example", "policy/user-interface"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "policy/policy-scope-digest.json").write_text(json.dumps({
        "digests": [{"root_folder": folder} for folder in ("src", "actions/data-types", "actions/technical-skills")],
    }))
    (root / "src/example.ts").write_text("export const value = 1;\n")
    (root / "policy/user-interface/back-navigation.policy.yaml").write_text(
        policy_source if policy_source is not None else
        "title: Back navigation policy\nobjective: Keep navigation safe.\npolicy_content: Use the shared back hook.\nreview_checklist:\n  - Uses the shared back hook.\n"
    )
    return root


def _fixture(
    case: unittest.TestCase, *, security_exceptions: list[str] | None = None,
    privacy_exceptions: list[str] | None = None,
) -> Path:
    root = _renderer_fixture(case)
    (root / "policy/user-interface/back-navigation.policy.yaml").unlink()
    (root / "policy/user-interface").rmdir()
    for field, title, objective, content in (
        ("access", "Security policy", "Protect access.", "Use primitives."),
        ("privacy", "Privacy policy", "Protect privacy.", "Limit disclosure."),
    ):
        (root / f"policy/{field}").mkdir()
        stem = "security" if field == "access" else "privacy"
        (root / f"policy/{field}/{stem}.policy.yaml").write_text(
            f"title: {title}\nobjective: {objective}\npolicy_content: {content}\nreview_checklist:\n  - Follows the policy.\n"
        )
    (root / "actions/data-types/example.ts").write_text("export type Example = string;\n")
    (root / "policy/README.md").write_text("# Policy instructions\n\nRoot Markdown is not enforced.\n")
    (root / "policy/TODO-SECURITY.md").write_text("# Security TODO\n\nRoot Markdown remains unchanged.\n")
    _git(root, "init", "-q")
    render_policy_documents(root=root)
    _complete(root / "policy/access/security.md", ["src/example.ts"] if security_exceptions is None else security_exceptions)
    _complete(root / "policy/privacy/privacy.md", privacy_exceptions)
    _git(root, "add", ".")
    _store_digest(root)
    _commit(root)
    return root


def _store_digest(root: Path) -> None:
    _write_stored_digest(root, _hash_policy_roots(root))


def _run_cli(root: Path, operation: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["POLICY_BASE_REVISION"] = "HEAD"
    return subprocess.run(
        [sys.executable, "-m", "agentic_devkit.cli.main", "policy", operation,
         "--root", str(root), *arguments],
        cwd=PROJECT_ROOT, env=environment, capture_output=True, text=True,
    )
