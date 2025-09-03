from typing import List, Dict, Any

def render_report(recs: List[Dict[str, Any]], risk: Dict[str, Any], payload) -> str:
    lines = [f"### Итог\n- Риск: **{risk['severity'].title()} ({risk['score']}/100)**."]
    if recs:
        lines.append("\n**Рекомендации:**")
        for r in recs:
            if r["type"] == "index":
                lines.append(f"- {r['title']}: `{r['action']['ddl']}`")
            elif r["type"] == "db_setting":
                lines.append(f"- {r['title']}: `{r['action']['alter']}`")
            else:
                lines.append(f"- {r['title']}")
    return "\n".join(lines)
