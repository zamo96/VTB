# src/presentation/formatter.py
from typing import Dict, Any, List

SEV_EMOJI = {"info":"ℹ️", "warning":"🟠", "critical":"🔴", "blocker":"🛑"}

def format_adviser_human(resp: Dict[str, Any], style: str = "md", verbosity: str = "short") -> str:
    risk = resp.get("risk", {})
    recs: List[Dict[str, Any]] = resp.get("recommendations", [])
    sev = (risk.get("severity") or "info").lower()
    emoji = SEV_EMOJI.get(sev, "ℹ️")
    score = risk.get("score", 0)
    drivers = risk.get("drivers") or []
    conf = risk.get("confidence_factor")

    # Заголовок
    lines = []
    if style == "md":
        lines.append(f"### Итог\n- Риск: **{emoji} {sev.title()} ({score}/100)**")
        if drivers:
            lines.append(f"- Драйверы: " + ", ".join(drivers))
        if conf is not None:
            lines.append(f"- Confidence factor: {conf}")
        lines.append("")
    else:
        lines.append(f"Итог: {sev.title()} {score}/100 {('['+', '.join(drivers)+']') if drivers else ''}")

    # Рекомендации
    if recs:
        if style == "md":
            lines.append("### Рекомендации (по приоритету)")
        else:
            lines.append("Рекомендации:")

        for r in recs:
            title = r.get("title") or "Recommendation"
            action = r.get("action", {})
            effort = r.get("effort")
            conf = r.get("confidence")
            why_nodes = "; ".join(
                f"nodeId: {e.get('nodeId')}, relation: {e.get('relation')}"
                for e in (r.get("evidence") or [])
            )

            # шапка пункта
            if style == "md":
                lines.append(f"- {title}")
                if why_nodes:
                    lines.append(f"  - Почему: {why_nodes}")
            else:
                lines.append(f"- {title} ({why_nodes})")

            # действия
            ddl = action.get("ddl")
            alter = action.get("alter")
            rewrite = action.get("rewrite_sql_hint")
            if rewrite:
                if style == "md":
                    lines.append(f"  - Что сделать: {rewrite}")
                else:
                    lines.append(f"  - Переписать: {rewrite}")
            if ddl:
                if style == "md":
                    lines.append(f"  - DDL: `{ddl}`")
                    lines.append(f"    • rollback: `DROP INDEX CONCURRENTLY {ddl.split(' ON ')[0].split()[-1]};`")
                    lines.append(f"    • после создания: выполнить ANALYZE")
                else:
                    lines.append(f"  - DDL: {ddl}")
            if alter:
                lines.append(f"  - ALTER: {alter}")

            # мета
            eg = r.get("expected_gain", {})
            gain_kind = eg.get("kind")
            gain_src = eg.get("source")
            if style == "md":
                lines.append(f"  - Как это поможет: тип: {gain_kind}; оценка: {gain_src}")
                if effort or conf:
                    lines.append(f"  - вложение: {effort or 'n/a'}; уверенность: {conf or 'n/a'}")
            else:
                lines.append(f"  - Эффект: {gain_kind}/{gain_src}; Effort: {effort}; Conf: {conf}")

            if verbosity == "short":
                # в кратком режиме не расписываем дальше
                continue

        # пустая строка в конце блока
        lines.append("")
    else:
        lines.append("_Проблем не найдено._" if style == "md" else "Проблем не найдено.")

    return "\n".join(lines)
