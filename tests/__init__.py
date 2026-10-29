# Lets `python -m unittest tests/test_x.py` find the helpers and the skill package.
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent / "skills" / "aiediting"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
