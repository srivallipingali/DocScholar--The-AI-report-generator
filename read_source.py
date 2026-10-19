from pathlib import Path

source_path = Path("samples/source.txt")
content = source_path.read_text(encoding="utf-8")

print(content)