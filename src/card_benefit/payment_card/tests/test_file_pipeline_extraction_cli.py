from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from payment_card.file_pipeline.extraction.cli import main
from payment_card.file_pipeline.extraction.llm_adapter import create_llm_call


class ExtractionCliTest(unittest.TestCase):
    def test_adapter_uses_injected_client_without_exposing_key(self):
        captured = {}

        class FakeResponse:
            content = "응답"

        class FakeClient:
            def invoke(self, prompt):
                captured["prompt"] = prompt
                return FakeResponse()

        def factory(**kwargs):
            captured.update(kwargs)
            return FakeClient()

        with patch.dict(os.environ, {"TEST_LLM_KEY": "secret-value"}):
            call = create_llm_call("test-model", "TEST_LLM_KEY", client_factory=factory)
        self.assertEqual(call("질문"), "응답")
        self.assertEqual(captured, {"model": "test-model", "api_key": "secret-value", "prompt": "질문"})

    def test_key_whitespace_and_carriage_return_are_stripped(self):
        captured = {}

        class FakeClient:
            def invoke(self, prompt):
                return "응답"

        def factory(**kwargs):
            captured.update(kwargs)
            return FakeClient()

        with patch.dict(os.environ, {"TEST_LLM_KEY": " secret-value\r\n"}):
            create_llm_call("test-model", "TEST_LLM_KEY", client_factory=factory)
        self.assertEqual(captured["api_key"], "secret-value")

    def test_missing_key_error_names_variable_but_not_value(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TEST_LLM_KEY") as caught:
                create_llm_call("test-model", "TEST_LLM_KEY")
        self.assertNotIn("secret", str(caught.exception))

    def test_sdk_exception_is_sanitized(self):
        class FakeClient:
            def invoke(self, prompt):
                raise RuntimeError("secret-value leaked by SDK")

        with patch.dict(os.environ, {"TEST_LLM_KEY": "secret-value"}):
            call = create_llm_call("test-model", "TEST_LLM_KEY", client_factory=lambda **_: FakeClient())
        with self.assertRaises(RuntimeError) as caught:
            call("질문")
        self.assertNotIn("secret-value", str(caught.exception))

    def test_sdk_exception_includes_safe_chain_and_metadata(self):
        class ConnectError(Exception):
            pass

        class APIConnectionError(Exception):
            status_code = 503
            code = "connection_error"
            type = "api_error"

        root = ConnectError("sk-root-secret")
        error = APIConnectionError("api_key=secret-value")
        error.__cause__ = root

        class FakeClient:
            def invoke(self, prompt):
                raise error

        with patch.dict(os.environ, {"TEST_LLM_KEY": "secret-value"}):
            call = create_llm_call("test-model", "TEST_LLM_KEY", client_factory=lambda **_: FakeClient())
        with self.assertRaises(RuntimeError) as caught:
            call("질문")

        message = str(caught.exception)
        self.assertIn("APIConnectionError", message)
        self.assertIn("ConnectError", message)
        self.assertIn("503", message)
        self.assertIn("connection_error", message)
        self.assertIn("api_error", message)
        self.assertNotIn("sk-", message)
        self.assertNotIn("secret-value", message)

    def test_run_dry_run_does_not_create_output_and_rejects_repo_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chunks = root / "chunks"
            chunks.mkdir()
            (chunks / "doc.chunks.json").write_text('{"chunks": []}', encoding="utf-8")
            self.assertEqual(main(["run", "--chunk-dir", str(chunks), "--output-dir", str(root / "out")]), 0)
        repo_root = Path(__file__).resolve().parents[4]
        self.assertEqual(main(["run", "--chunk-dir", ".", "--output-dir", str(repo_root / "unsafe")]), 2)


if __name__ == "__main__":
    unittest.main()
