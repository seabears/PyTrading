"""인자 없는 설정 로드와 OS 실행 잠금의 동작을 검증한다."""
import json
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path

from paths import PROJECT_ROOT
from app.runtime import AlreadyRunningError, SETTINGS_PATH, acquire_run_lock, load_run_settings, release_run_lock


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix=".test-", dir=Path(__file__).parent)
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.path = self.root / "settings.json"
        self.settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        self.settings["collect_news"] = True  # 켜진 뉴스 설정을 읽는 회귀 검증용 입력
        self.settings["env_file"] = "credentials/toss.env"
        # 이 테스트는 경로·설정 해석을 검사한다. 실제 관찰 목록 변경에 의존하지 않는다.
        self.settings["output_dir"] = "../Data/paper"
        self.settings["symbols"] = ["KR:005930", "US:AAPL"]
        self.write_settings()

    def write_settings(self):
        self.path.write_text(json.dumps(self.settings), encoding="utf-8")

    def test_continuous_configuration_can_enable_news(self):
        loaded = load_run_settings(self.path, project_root=self.root)
        self.assertTrue(loaded["watch"])
        self.assertTrue(loaded["collect_news"])
        self.assertEqual(loaded["output_dir"], self.root.parent / "Data/paper")
        self.assertEqual(loaded["events_file"], self.root.parent / "Data/confirmed-events.json")
        self.assertEqual(loaded["env_file"], self.root / "credentials" / "toss.env")
        self.assertEqual(loaded["symbols"], [("KR", "005930"), ("US", "AAPL")])

    def test_invalid_intervals_booleans_and_symbols(self):
        original = dict(self.settings)
        for name, value in (("interval", 0), ("interval", True), ("news_interval", 10),
                            ("watch", "true"), ("symbols", []), ("symbols", ["BAD"])):
            self.settings = {**original, name: value}
            self.write_settings()
            with self.assertRaises(ValueError):
                load_run_settings(self.path)

    def test_unknown_setting_rejected(self):
        self.settings["typo"] = 60
        self.write_settings()
        with self.assertRaises(ValueError):
            load_run_settings(self.path)

    def test_old_lock_file_does_not_block_restart(self):
        path = self.root / "run.lock"
        path.write_text("old process", encoding="utf-8")
        first = acquire_run_lock(path)
        try:
            with self.assertRaises(AlreadyRunningError):
                acquire_run_lock(path)
        finally:
            release_run_lock(first)
        restarted = acquire_run_lock(path)
        release_run_lock(restarted)

    def test_forced_process_exit_releases_os_lock(self):
        path = self.root / "run.lock"
        ready = self.root / "ready"
        # 부모와 다른 프로세스가 잠금을 보유한 채 강제 종료되는 상황을 확인한다.
        script = ("import sys,time; from pathlib import Path; "
                  "from app.runtime import acquire_run_lock; "
                  "held=acquire_run_lock(Path(sys.argv[1])); "
                  "Path(sys.argv[2]).write_text('locked'); time.sleep(30)")
        child = subprocess.Popen([sys.executable, "-B", "-X", "utf8", "-c", script, str(path), str(ready)],
                                 cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists(), "별도 프로세스가 잠금을 획득하지 못했습니다.")
            with self.assertRaises(AlreadyRunningError):
                acquire_run_lock(path)
        finally:
            child.terminate()
            child.communicate(timeout=5)
        restarted = acquire_run_lock(path)
        release_run_lock(restarted)


if __name__ == "__main__":
    unittest.main()
