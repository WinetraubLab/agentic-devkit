"""Expose policy rendering and verification through the toolkit CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from jinja2 import TemplateError

from .policy_scope import _hash_policy_roots
from .render_policy_documents import render_policy_documents
from .verify_policy_attestations import verify_policy_attestations, _write_stored_digest


def add_policy_parser(groups: argparse._SubParsersAction) -> None:
    """Register the policy command group."""
    parser = groups.add_parser("policy", help="render policies and verify attestations")
    commands = parser.add_subparsers(dest="policy_command", required=True)
    for name, help_text in (
        ("verify", "verify current attestations against the committed baseline"),
        ("render", "regenerate policies with empty attestations and update the digest"),
        ("check-documents", "check generated policy bodies without writing"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--root", type=Path, help="repository root; defaults to the current Git root")
        if name == "verify":
            command.add_argument("--baseline-ref", help="Git revision supplying finding allowances")


def run_policy_command(args: argparse.Namespace) -> int:
    """Run one policy operation, preserving v0's success/failure exit statuses."""
    root = args.root
    try:
        if args.policy_command == "render":
            digests = _hash_policy_roots(root)
            result = render_policy_documents(root=root)
            _write_stored_digest(root, digests)
            print(
                f"Rendered {len(result.source_paths)} policy documents with empty "
                f"attestations ({len(result.changed_paths)} changed)."
            )
        elif args.policy_command == "check-documents":
            result = render_policy_documents(root=root, check=True)
            print(f"Generated policy documents are current ({len(result.source_paths)} checked).")
        else:
            result = verify_policy_attestations(root=root, baseline_revision=args.baseline_ref)
            print(
                f"Policy attestations do not exceed {result.baseline_revision} "
                f"for policy scope digest {result.digest}."
            )
    except (ValueError, OSError, TemplateError, subprocess.CalledProcessError) as error:
        print(f"\n{error}\n", file=sys.stderr)
        return 1
    return 0
