# src/advisor/rules_loader.py
import os, yaml
from typing import List, Dict, Any
from .feature_catalog import is_valid_feature_kind

ALLOWED_TYPES = {"index", "db_setting", "sql_rewrite", "stats"}

def _rule_is_actionable(rule: Dict[str, Any]) -> bool:
    t = (rule.get("type") or "").strip()
    act = rule.get("action") or {}

    if t == "index":
        return bool(act.get("ddl_template"))
    if t == "db_setting":
        return bool(act.get("alter"))
    if t == "sql_rewrite":
        # допускаем rewrite_sql_hint или ddl_template (если хочешь DDL)
        return bool(act.get("rewrite_sql_hint") or act.get("ddl_template"))
    if t == "stats":
        return bool(act.get("ddl_template") or act.get("alter"))
    return False

def load_rules(dir_path: str | None = None) -> List[Dict[str, Any]]:
    dir_path = dir_path or os.environ.get("RULES_DIR", "src/rules/ruleset-v1")
    collected: List[Dict[str, Any]] = []
    if not os.path.isdir(dir_path):
        print(f"[rules_loader] WARNING: rules dir not found: {dir_path}")
        return collected

    for name in sorted(os.listdir(dir_path)):
        if not (name.endswith(".yaml") or name.endswith(".yml")):
            continue
        path = os.path.join(dir_path, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[rules_loader] skip {name}: read error: {e}")
            continue

        data.setdefault("id", os.path.splitext(name)[0])

        # 1) обязательный match.feature
        match = data.get("match") or {}
        fk = (match.get("feature") or "").strip()
        if not fk:
            print(f"[rules_loader] skip {name}: no match.feature")
            continue
        if not is_valid_feature_kind(fk):
            print(f"[rules_loader] skip {name}: unknown feature '{fk}'")
            continue

        # 2) валидный type
        t = (data.get("type") or "").strip()
        if t not in ALLOWED_TYPES:
            print(f"[rules_loader] skip {name}: invalid type '{t}'")
            continue

        # 3) есть «действие»
        if not _rule_is_actionable(data):
            print(f"[rules_loader] skip {name}: rule not actionable (no ddl/alter/rewrite)")
            continue

        collected.append(data)

    print(f"[rules_loader] loaded {len(collected)} rules from {dir_path}")
    return collected
