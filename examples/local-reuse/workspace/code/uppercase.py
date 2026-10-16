from pathlib import Path
root = Path(__file__).resolve().parents[1]
(root / "outputs/uppercase.txt").write_text((root / "inputs/source.txt").read_text().upper())
