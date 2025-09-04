import os, yaml
from functools import lru_cache
from typing import Set

@lru_cache
def load_feature_kinds() -> Set[str]:
    path = os.environ.get("FEATURE_KINDS_FILE", "src/advisor/feature_kinds.yaml")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        return set(map(str, data))
    # fallback + предупреждение в лог
    print(f"[feature_catalog] WARNING: {path} not found; using fallback list.")

def is_valid_feature_kind(kind: str) -> bool:
    return kind in load_feature_kinds()
