#!/usr/bin/env python3
"""Tests for the workflow package validator and builder.

Run with:
    python3 -m unittest discover -s tools -p 'test_*.py'
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402
import validate  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

MANIFEST = """\
resolver = 1
title = "Test Workflow"
identifier = "test.workflow-examples"
namespace = "official"
kind = "workflow"
version = "1.2.3"
description = "Test package."
license = "Apache-2.0"
"""


def document() -> dict:
    return {
        "schemaVersion": 2,
        "name": "Test workflow",
        "version": "1.2.3",
        "nodes": [
            {"id": "start", "type": "workflow", "data": {"kind": "start"}},
            {"id": "agent", "type": "workflow", "data": {"kind": "agent", "agentConfig": {"prompt": "hi"}}},
            {"id": "output", "type": "workflow", "data": {"kind": "output"}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "agent"},
            {"id": "e2", "source": "agent", "target": "output"},
        ],
    }


class PackageCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.write_manifest(MANIFEST)
        self.workflows = self.root / "assets" / "workflows"
        self.workflows.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_manifest(self, content: str) -> None:
        (self.root / "orax.toml").write_text(content, encoding="utf-8")

    def write_document(self, content: dict | str, name: str = "workflow.json") -> Path:
        path = self.workflows / name
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        return path

    def codes(self) -> list[str]:
        return [item["code"] for item in validate.validate_package(self.root)]


class ValidPackageTests(PackageCase):
    def test_accepts_a_complete_package(self) -> None:
        self.write_document(document())
        self.assertEqual(self.codes(), [])

    def test_accepts_the_repository_examples(self) -> None:
        self.assertEqual(validate.validate_package(PACKAGE_ROOT), [])

    def test_build_is_deterministic(self) -> None:
        self.write_document(document())
        first, first_digest = build.build_package(self.root, self.root / "dist")
        second, second_digest = build.build_package(self.root, self.root / "dist")
        self.assertEqual(first_digest, second_digest)
        self.assertEqual(first.read_bytes(), second.read_bytes())


class LayoutTests(PackageCase):
    def test_requires_the_workflows_directory(self) -> None:
        self.workflows.rmdir()
        self.assertIn("workflows_directory_missing", self.codes())

    def test_requires_at_least_one_document(self) -> None:
        (self.workflows / "README.md").write_text("ignored", encoding="utf-8")
        self.assertIn("workflows_directory_empty", self.codes())

    def test_ignores_non_json_and_subdirectories(self) -> None:
        self.write_document(document())
        (self.workflows / "README.md").write_text("ignored", encoding="utf-8")
        (self.workflows / "nested").mkdir()
        (self.workflows / "nested" / "hidden.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.codes(), [])

    def test_requires_the_manifest(self) -> None:
        self.write_document(document())
        (self.root / "orax.toml").unlink()
        self.assertIn("manifest_missing", self.codes())


class ManifestTests(PackageCase):
    def test_rejects_another_kind(self) -> None:
        self.write_manifest(MANIFEST.replace('kind = "workflow"', 'kind = "agent"'))
        self.write_document(document())
        self.assertIn("manifest_kind_invalid", self.codes())

    def test_rejects_a_kind_specific_section(self) -> None:
        self.write_manifest(MANIFEST + '\n[webview]\nstart_url = "https://example.invalid"\n')
        self.write_document(document())
        self.assertIn("manifest_section_not_allowed", self.codes())

    def test_rejects_a_targeted_artifact(self) -> None:
        self.write_manifest(MANIFEST + '\n[[targets]]\ntarget = "x86_64-unknown-linux-gnu"\n')
        self.write_document(document())
        self.assertIn("manifest_section_not_allowed", self.codes())

    def test_rejects_an_invalid_identifier(self) -> None:
        self.write_manifest(MANIFEST.replace('identifier = "test.workflow-examples"', 'identifier = "Test"'))
        self.write_document(document())
        self.assertIn("manifest_identifier_invalid", self.codes())


class DocumentTests(PackageCase):
    def test_rejects_invalid_json(self) -> None:
        self.write_document("{ not json")
        self.assertIn("document_invalid_json", self.codes())

    def test_requires_a_name(self) -> None:
        body = document()
        body.pop("name")
        self.write_document(body)
        self.assertIn("document_name_missing", self.codes())

    def test_rejects_an_unsupported_node_kind(self) -> None:
        body = document()
        body["nodes"][1]["data"]["kind"] = "loop"
        self.write_document(body)
        self.assertIn("node_kind_unsupported", self.codes())

    def test_rejects_an_empty_skills_array(self) -> None:
        # The gate refuses a present, non-null field even when it is empty. This is
        # why the examples omit `skills` and `mcps` entirely instead of writing [].
        body = document()
        body["nodes"][1]["data"]["agentConfig"]["skills"] = []
        self.write_document(body)
        self.assertIn("node_config_unsupported", self.codes())

    def test_allows_an_explicit_null_field(self) -> None:
        body = document()
        body["nodes"][1]["data"]["agentConfig"]["skills"] = None
        self.write_document(body)
        self.assertEqual(self.codes(), [])

    def test_requires_exactly_one_start(self) -> None:
        body = document()
        body["nodes"].append({"id": "start-2", "type": "workflow", "data": {"kind": "start"}})
        self.write_document(body)
        self.assertIn("start_node_count", self.codes())

    def test_rejects_a_dangling_edge(self) -> None:
        body = document()
        body["edges"].append({"id": "e3", "source": "agent", "target": "missing"})
        self.write_document(body)
        self.assertIn("edge_endpoint_unknown", self.codes())

    def test_rejects_a_duplicate_node_id(self) -> None:
        body = document()
        body["nodes"].append({"id": "agent", "type": "workflow", "data": {"kind": "agent"}})
        self.write_document(body)
        self.assertIn("node_id_duplicate", self.codes())

    def test_rejects_a_cycle(self) -> None:
        body = document()
        body["edges"].append({"id": "e3", "source": "output", "target": "agent"})
        self.write_document(body)
        self.assertIn("graph_cycle", self.codes())


class SlotTests(PackageCase):
    def named_slot_document(self) -> dict:
        body = document()
        body["executorSlots"] = [{"name": "writer", "description": "Writes well."}]
        body["nodes"][1]["data"]["agentConfig"]["executorSlot"] = "writer"
        return body

    def test_accepts_a_declared_slot(self) -> None:
        self.write_document(self.named_slot_document())
        self.assertEqual(self.codes(), [])

    def test_rejects_an_undeclared_slot(self) -> None:
        body = document()
        body["nodes"][1]["data"]["agentConfig"]["executorSlot"] = "writer"
        self.write_document(body)
        self.assertIn("slot_not_declared", self.codes())

    def test_rejects_the_reserved_default_slot(self) -> None:
        body = self.named_slot_document()
        body["executorSlots"][0]["name"] = "default"
        self.write_document(body)
        self.assertIn("slot_name_reserved", self.codes())

    def test_rejects_a_duplicate_slot(self) -> None:
        body = self.named_slot_document()
        body["executorSlots"].append({"name": "writer", "description": "Again."})
        self.write_document(body)
        self.assertIn("slot_name_duplicate", self.codes())

    def test_rejects_a_missing_description(self) -> None:
        body = self.named_slot_document()
        body["executorSlots"][0]["description"] = "  "
        self.write_document(body)
        self.assertIn("slot_description_invalid", self.codes())

    def test_rejects_a_malformed_hint(self) -> None:
        body = self.named_slot_document()
        body["executorSlots"][0]["hint"] = {"agentCli": 7}
        self.write_document(body)
        self.assertIn("slot_hint_invalid", self.codes())


if __name__ == "__main__":
    unittest.main()
