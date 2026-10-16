import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
text = (root / "outputs/uppercase.txt").read_text()
(root / "outputs/count.json").write_text(json.dumps({"characters": len(text)}, sort_keys=True) + "\n")
