"""run_fp_chat.py 진입점 시험: DB·OpenAI 호출 없이 화면 로딩 경로만 확인한다.

install()이 sys.modules['llm']을 바꾸므로 각 경우를 별도 프로세스에서 실행한다.
"""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ENTRY = Path(__file__).resolve().parents[1] / "file_pipeline" / "chat" / "run_fp_chat.py"
SRC = Path(__file__).resolve().parents[3].parent  # .../src

SCRIPT = """
import sys
from streamlit.testing.v1 import AppTest
at = AppTest.from_file({entry!r}, default_timeout=60)
at.run()
print("EXC", len(at.exception))
print("ERR", [e.value for e in at.error])
print("INFO", [i.value for i in at.info])
"""


def _run(env_extra):
    env = {k: v for k, v in os.environ.items() if k not in ("OPENAI_API_KEY", "DB_URL")}
    env.update(env_extra)
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), str(SRC / "card_benefit")])
    return subprocess.run(
        [sys.executable, "-c", SCRIPT.format(entry=str(ENTRY))],
        capture_output=True, text=True, timeout=120, env=env,
    ).stdout


class RunEntryTest(unittest.TestCase):
    def test_missing_key_shows_message_instead_of_crashing(self):
        out = _run({})
        self.assertIn("EXC 0", out)
        self.assertIn("OPENAI_API_KEY", out)

    def test_with_key_loads_fp_chat_mode_without_network(self):
        out = _run({"OPENAI_API_KEY": "dummy-no-call"})
        self.assertIn("EXC 0", out)
        self.assertIn("우리 카드 데이터(fp_chat) 모드", out)


if __name__ == "__main__":
    unittest.main()
