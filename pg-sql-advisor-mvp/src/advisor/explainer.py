from typing import List, Dict, Any

def render_report(recs: List[Dict[str, Any]], risk: Dict[str, Any], payload) -> str:
    lines = [
        f"### Итог",
        f"- Риск: **{risk['severity'].title()} ({risk['score']}/100)**",
        "- Драйверы: " + ", ".join(risk.get("drivers", [])) if risk.get("drivers") else "- Драйверы: не выявлены",
        ""
    ]
    if recs:
        lines.append("### Рекомендации (по приоритету)")
        for r in recs:
            action = r.get("action", {})
            if "ddl" in action:
                lines.append(f"- {r['title']}\n  - DDL: `{action['ddl']}`")
            elif "alter" in action:
                lines.append(f"- {r['title']}\n  - ALTER: `{action['alter']}`")
            else:
                lines.append(f"- {r['title']}")
    else:
        lines.append("_Проблем не найдено._")
    return "\n".join(lines)
