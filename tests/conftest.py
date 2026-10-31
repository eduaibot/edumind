import sys
from pathlib import Path

# Optional local dependency directory used for this workspace's isolated checks.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / ".test-deps").exists():
    sys.path.insert(0, str(ROOT / ".test-deps"))
