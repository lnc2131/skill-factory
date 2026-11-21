import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "skills" / "{{name}}" / "scripts" / "main.py"


def test_script_prints_json():
    out = subprocess.run([sys.executable, str(SCRIPT), "hello"], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == {"input": "hello", "length": 5}
