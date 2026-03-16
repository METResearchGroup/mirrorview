import subprocess

from backend.lib.constants import ROOT_DIR


def get_git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(ROOT_DIR),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:12]
        raise RuntimeError(
            f"Failed to get git hash (exit={result.returncode}): {result.stderr.strip()}"
        )
    except Exception as e:
        raise RuntimeError("Failed to get git hash") from e
