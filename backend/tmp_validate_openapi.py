from pathlib import Path
import yaml

p = Path(__file__).resolve().parent.parent / "docs" / "openapi.yaml"
text = p.read_text(encoding="utf-8")
data = yaml.safe_load(text)

print("YAML_OK")
print("PATH_COUNT=", len(data.get("paths", {})))
print(
    "HAS_BOOK_PROCESSING_STATUS_RESPONSE=",
    "BookProcessingStatusResponse" in data.get("components", {}).get("schemas", {}),
)
