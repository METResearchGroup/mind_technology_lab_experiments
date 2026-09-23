import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "autoresearch"
    / "learning_user_simulators_with_turing_rewards_2026_09_09"
    / "jobs"
    / "train_qwen3_8b_turing_rl.py"
)


def test_qwen3_8b_job_script_self_test() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--self-test"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "self-test ok" in result.stdout
