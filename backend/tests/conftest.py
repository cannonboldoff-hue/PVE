import os
import sys
import tempfile
from pathlib import Path

os.environ["PVE_DATA"] = tempfile.mkdtemp(prefix="pve_test_")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
