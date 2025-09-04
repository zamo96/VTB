import os
from pathlib import Path
from typing import Any, Dict, List
import yaml

from src.advisor.feature_catalog import is_valid_feature_kind

def _candidate_dirs() -> List[Path]:
    # 1) ENV
    env_dir = os.getenv("RULES_DIR")
    candidates = []
    if env_dir:
        candidates.append(Path(env_dir))

    # 2) рядом с модулем
    here = Path(__file__).resolve().parent
    candidates += [
        here / "rules" / "ruleset-v1",
        here.parent / "rules" / "ruleset-v1",  # src/advisor/.. → src/rules/ruleset-v1
    ]

    # 3) относительно CWD (когда запускаем uvicorn из корня)
    cwd = Path.cwd()
    candidates += [
        cwd / "src" / "rules" / "ruleset-v1",
        cwd / "rules" / "ruleset-v1",
    ]

    # Уникализируем и возвращаем
    seen = set()
    uniq = []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq

def load_rules(dir_path: str | None = None) -> List[Dict[str, Any]]:
    paths = [Path(dir_path)] if dir_path else _candidate_dirs()

    rules: List[Dict[str, Any]] = []
    chosen: Path | None = None

    for p in paths:
        if p and p.exists() and p.is_dir():
            yaml_files = sorted(p.glob("*.yaml"))
            if yaml_files:
                chosen = p
                for yf in yaml_files:
                    try:
                        with open(yf, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f) or {}
                    except Exception as e:
                        print(f"[rules_loader] skip {yf.name}: YAML error={e}")
                        continue

                    # валидация feature.kind (минимум)
                    match = data.get("match") or {}
                    fk = match.get("feature")
                    if fk and not is_valid_feature_kind(fk):
                        print(f"[rules_loader] skip {yf.name}: unknown feature '{fk}'")
                        continue

                    # нормализация id
                    rid = data.get("id") or yf.stem.upper()
                    data["id"] = rid
                    rules.append(data)
                break

    if not chosen:
        print(f"[rules_loader] WARNING: rules dir not found in candidates: "
              f"{[str(p) for p in paths]}")
    else:
        print(f"[rules_loader] loaded {len(rules)} rules from {chosen}")
    return rules
