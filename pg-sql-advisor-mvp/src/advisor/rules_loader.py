import os
import yaml
from typing import List, Dict, Any

def load_rules(dir_path: str | None = None) -> List[Dict[str, Any]]:
    dir_path = dir_path or os.environ.get("RULES_DIR", "src/rules/ruleset-v1")
    rules: List[Dict[str, Any]] = []
    if not os.path.isdir(dir_path):
        return rules
    for name in sorted(os.listdir(dir_path)):
        if name.endswith(".yaml"):
            with open(os.path.join(dir_path, name), "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                data.setdefault("id", name[:-5])
                rules.append(data)
    return rules
