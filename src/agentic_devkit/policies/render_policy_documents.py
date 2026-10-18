"""Render YAML policy sources and check their generated Markdown bodies."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Sequence

from jinja2 import Environment, StrictUndefined
import yaml

from .policy_scope import _is_relative_folder, load_policy_scope

POLICY_SOURCE_SUFFIX = ".policy.yaml"
ATTESTATION_HEADING = "# Attestation"
REQUIRED_FIELDS = ("title", "objective", "policy_content")


class _PolicyLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys, as v0's YAML parser does."""


# v0 uses YAML 1.2: yes/on and dates remain strings, unlike SafeLoader's 1.1 defaults.
_PolicyLoader.yaml_implicit_resolvers = {
    char: [(tag, pattern) for tag, pattern in resolvers if tag not in {
        "tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp",
    }]
    for char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_PolicyLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def _construct_mapping(loader: _PolicyLoader, node: yaml.MappingNode) -> dict:
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"Duplicate YAML key: {key}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node)
    return mapping


_PolicyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping,
)


@dataclass
class PolicyDocument:
    source_path: Path
    output_path: Path


@dataclass
class RenderResult:
    changed_paths: list[Path]
    policy_documents: list[PolicyDocument]
    source_paths: list[Path]


def _list_sources(directory: Path) -> list[Path]:
    paths = []
    for path in directory.iterdir():
        if path.is_symlink():
            raise ValueError(f"Policy rendering does not allow symbolic links: {path}")
        if path.is_dir():
            paths.extend(_list_sources(path))
        elif path.is_file() and path.name.endswith(POLICY_SOURCE_SUFFIX):
            paths.append(path)
    return sorted(paths)


def _generated_body(markdown: str, label: str) -> str:
    headings = list(re.finditer(r"^# Attestation[ \t]*$", markdown, re.MULTILINE))
    if len(headings) != 1:
        raise ValueError(f"{label} must contain exactly one {ATTESTATION_HEADING} heading.")
    return markdown[:headings[0].end()].rstrip()


def _read_source(path: Path, root: Path) -> dict:
    label = path.relative_to(root).as_posix()
    try:
        source = yaml.load(path.read_bytes().decode("utf-8"), Loader=_PolicyLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"{label} contains invalid YAML: {error}") from error
    if not isinstance(source, dict):
        raise ValueError(f"{label} must contain a YAML object.")
    unknown = [str(field) for field in source if field not in (*REQUIRED_FIELDS, "review_checklist", "applicable_folders", "exemptions")]
    if unknown:
        raise ValueError(f"{label} contains unknown fields: {', '.join(unknown)}.")
    for field in REQUIRED_FIELDS:
        value = source.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} requires a non-empty {field} string.")
    for field, limit in (("review_checklist", 25), ("exemptions", 50)):
        entries = source.get(field, [])
        if (not isinstance(entries, list) or (field == "review_checklist" and not entries)
            or any(not isinstance(item, str) or not item.strip() for item in entries)):
            raise ValueError(f"{label} requires a {'non-empty ' if field == 'review_checklist' else ''}{field} list of non-empty strings.")
        for index, item in enumerate(entries, start=1):
            if len(item.split()) > limit:
                raise ValueError(f"{label} {field} entry {index} exceeds {limit} words.")
        source[field] = [" ".join(item.split()) for item in entries]
    return source


def _applicable_folders(source: dict, scope: tuple[str, ...], root: Path, label: str) -> list[str]:
    folders = source.get("applicable_folders", "all")
    if folders == "all":
        return list(scope)
    if not isinstance(folders, list) or not folders:
        raise ValueError(f"{label} applicable_folders must be all or a nonempty list of folders.")
    resolved_roots = [(root / directory).resolve() for directory in scope]
    seen = set()
    for folder in folders:
        if not _is_relative_folder(folder):
            raise ValueError(f"{label} contains an invalid applicable folder: {folder!r}.")
        if folder in seen:
            raise ValueError(f"{label} contains a duplicate applicable folder: {folder}.")
        seen.add(folder)
        path = (root / folder).resolve()
        if (
            not path.is_dir()
            or not any(path.is_relative_to(directory) for directory in resolved_roots)
        ):
            raise ValueError(f"{label} applicable folder must exist within the configured roots: {folder}.")
    return sorted(folders)


def render_policy_documents(
    *, root: Path | str | None = None, check: bool = False,
    output_paths: Sequence[Path | str] | None = None,
) -> RenderResult:
    """Render field policies, or check their bodies without changing attestations."""
    root = Path(os.path.abspath(root or Path.cwd()))
    scope = load_policy_scope(root)
    directory = root / "policy"
    template_path = Path(__file__).with_name("policy-template.md.j2")
    sources = sorted(
        source for field in directory.iterdir()
        if not field.is_symlink() and field.is_dir()
        for source in _list_sources(field)
    )
    if not sources:
        raise ValueError("No *.policy.yaml files were found under policy/<field>/.")
    selected = (
        {Path(os.path.abspath(path)) for path in output_paths}
        if output_paths is not None else None
    )
    environment = Environment(
        autoescape=False, undefined=StrictUndefined, keep_trailing_newline=True,
    )
    template = environment.from_string(template_path.read_bytes().decode("utf-8"))
    changed, documents = [], []
    for source_path in sources:
        output_path = source_path.with_name(
            source_path.name.removesuffix(POLICY_SOURCE_SUFFIX) + ".md"
        )
        source = _read_source(source_path, root)
        label = source_path.relative_to(root).as_posix()
        folders = _applicable_folders(source, scope, root, label)
        documents.append(PolicyDocument(source_path, output_path))
        if selected is not None and output_path not in selected:
            continue
        rendered = template.render(
            source,
            applicable_folders=folders, scope_directories=folders,
        )
        if check:
            label = output_path.relative_to(root).as_posix()
            current_body = (
                _generated_body(output_path.read_bytes().decode("utf-8"), label)
                if output_path.exists() else None
            )
            if current_body != _generated_body(rendered, label):
                changed.append(output_path)
        elif not output_path.exists() or output_path.read_bytes() != rendered.encode("utf-8"):
            changed.append(output_path)
            output_path.write_bytes(rendered.encode("utf-8"))
    if check and changed:
        paths = "\n".join(f"- {path.relative_to(root).as_posix()}" for path in changed)
        raise ValueError(
            "Generated policy documents are stale or were edited manually:\n"
            f"{paths}\n\nRun agentic-devkit policy render to regenerate them with empty attestations."
        )
    return RenderResult(changed, documents, sources)
