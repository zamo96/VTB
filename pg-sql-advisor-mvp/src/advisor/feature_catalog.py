import os, yaml
from functools import lru_cache
from typing import Set

# Набор по умолчанию — на случай, если YAML не найден.
DEFAULT_FEATURE_KINDS: Set[str] = {
    "seq_scan_big_table",
    "order_by_limit_no_covering_index",
    "like_leading_wildcard",
    "functional_index_candidate",
    "fk_missing_index",
    "nested_loop_no_inner_index",
    "sort_spill_risk",
    "hashagg_spill_risk",
    "outdated_stats",
    "index_only_possible",
}

@lru_cache
def load_feature_kinds() -> Set[str]:
    path = os.environ.get("FEATURE_KINDS_FILE", "src/advisor/feature_kinds.yaml")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        return set(map(str, data))
    # fallback + предупреждение в лог
    print(f"[feature_catalog] WARNING: {path} not found; using fallback list.")
    return DEFAULT_FEATURE_KINDS

def is_valid_feature_kind(kind: str) -> bool:
    return kind in load_feature_kinds()
