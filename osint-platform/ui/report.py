"""Report view — dedicated tab per agent (not the old formal expander list).

Each agent gets its own Streamlit tab: character avatar + name/role,
real status badge, tool chips, and ONLY that agent's Markdown output.
An Overview tab comes first: risk score, the ORACLE executive summary
excerpt, and a short per-agent summary — it does not duplicate the
full per-agent outputs (full text lives in each agent's tab only).
JSON + PDF downloads stay below the tabs. PDF mapping fix from v1 is
preserved: generate_pdf receives agent-keyed results.
"""
import html
import json
import re
from datetime import timezone

from ui.avatars import avatar_html
from ui.components import AGENT_ORDER


def _esc(v):
    return html.escape(str(v))


def extract_risk_score(text):
    for pattern in (
        r"[Rr]isk\s*[Ss]core[:\s]*(\d{1,3})",
        r"(\d{1,3})\s*/\s*100",
        r"(\d{1,3})\s*out\s*of\s*100",
        r"[Ss]core[:\s]*(\d{1,3})",
    ):
        match = re.search(pattern, text or "")
        if match and 0 <= int(match.group(1)) <= 100:
            return int(match.group(1))
    return None


def risk_level(score):
    if score is None:
        return "Not reported", "#91a1b2"
    if score >= 80:
        return "Critical", "#ff7373"
    if score >= 60:
        return "High", "#ffae69"
    if score >= 40:
        return "Moderate", "#f1cd72"
    if score >= 20:
        return "Low", "#66d5bb"
    return "Minimal", "#91a1b2"


def _is_legacy_round_limit(content):
    return (content or "").strip().lower().strip("_*() ") == "max rounds reached without final answer"


def _plain_snippet(content, limit=180):
    """First prose snippet of an agent output, markdown stripped, for Overview."""
    text = re.sub(r"[#>*`_]", "", content or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def agent_tab_data(results, activity, profiles):
    """Pure, unit-testable per-agent report data (no Streamlit needed).

    Returns one dict per agent: key, name, role, color, catchphrase,
    status, tools (list, in first-seen order), content, snippet.
    Content is that agent's output ONLY — tabs must never mix agents.
    """
    rows = []
    for key in AGENT_ORDER:
        agent = profiles[key]
        content = str(results.get(key, "")).strip()
        if _is_legacy_round_limit(content):
            content = ""
        record = (activity or {}).get(key, {}) or {}
        status = record.get("status", "complete" if content else "error")
        tool_events = [
            item for item in record.get("activity_log", [])
            if item.get("type") == "tool_call" and item.get("tool_name")
        ]
        tools = list(dict.fromkeys(item["tool_name"] for item in tool_events))
        rows.append({
            "key": key,
            "name": agent["name"],
            "role": agent["role"],
            "color": agent.get("color", "#FF2E88"),
            "catchphrase": agent.get("catchphrase", ""),
            "status": status,
            "tools": tools,
            "content": content,
            "snippet": _plain_snippet(content),
        })
    return rows


def _tab_header_html(row):
    """Character header for one agent tab: avatar, name/role, status, tools."""
    chips = ""
    if row["tools"]:
        chips = "".join(f'<span class="hero-badge">{_esc(t)}</span>' for t in row["tools"])
    else:
        chips = '<span class="hero-badge">TOOLS EXECUTED · none recorded</span>' if row["key"] != "oracle" else \
            '<span class="hero-badge">TOOLS EXECUTED · none (synthesis agent)</span>'
    return (
        f'<div class="char-card" style="--agent-accent:{_esc(row["color"])}">'
        f'<div class="char-portrait">{avatar_html(row["key"], row["status"], size=96)}</div>'
        f'<div class="char-name">{_esc(row["name"])}</div>'
        f'<div class="char-role">{_esc(row["role"])}</div>'
        f'<div class="char-catch">“{_esc(row["catchphrase"])}”</div>'
        f'<div class="char-status"><span class="char-dot"></span>{_esc(row["status"].replace("_", " ").upper())}</div>'
        f'<div style="margin-top:.6rem;display:flex;gap:.4rem;flex-wrap:wrap;justify-content:center">{chips}</div>'
        "</div>"
    )


def render_report(report, profiles, model_name):
    import streamlit as st

    results = report["results"]
    target = report["target"]
    target_type = report["target_type"]
    elapsed = report["elapsed"]
    oracle_text = str(results.get("oracle", ""))
    score = None if _is_legacy_round_limit(oracle_text) else extract_risk_score(oracle_text)
    activity = st.session_state.get("nexus_latest_activity", {})
    rows = agent_tab_data(results, activity, profiles)
    completed = sum(1 for r in rows if r["content"] and not r["content"].startswith("# Agent execution failed")
                    and not _is_legacy_round_limit(r["content"]))
    st.markdown(
        '<div class="section-heading"><div><span class="section-kicker">REPORT</span>'
        '<h2>Intelligence report</h2></div><span>One dedicated tab per specialist · tools shown by name</span></div>',
        unsafe_allow_html=True,
    )
    try:
        from datetime import datetime

        report_time = datetime.fromisoformat(report["timestamp"]).astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    except (ValueError, TypeError):
        report_time = str(report.get("timestamp", "Time not recorded"))
    st.markdown(
        '<div class="report-summary"><div class="report-summary-title">Analysis complete · ' + _esc(target) + '</div>'
        '<div class="report-summary-meta">' + _esc(target_type) + ' · ' + str(completed) + '/5 agents returned usable findings · '
        + f'{elapsed:.1f}s elapsed' + ' · ' + _esc(report_time) + '</div></div>',
        unsafe_allow_html=True,
    )
    level, color = risk_level(score)
    if score is None:
        risk_value = "—"
        risk_detail = "No verified numeric synthesis was available. Review the full findings below."
    else:
        risk_value = str(score)
        risk_detail = f"{level} exposure · reported by the synthesis agent on a 0–100 scale."
    st.markdown(
        '<div class="risk-panel" style="--risk-color:' + color + '"><div class="risk-number">' + risk_value
        + '<span style="font-size:.63rem;color:#8193a2">/100</span></div><div class="risk-copy"><strong>Reported risk assessment · '
        + _esc(level) + '</strong><span>' + _esc(risk_detail) + '</span></div></div>',
        unsafe_allow_html=True,
    )

    labels = ["Overview"] + [r["name"] for r in rows]
    tabs = st.tabs(labels)
    # Overview tab: risk + ORACLE excerpt + short per-agent summaries only.
    with tabs[0]:
        st.markdown("### Overview — executive summary")
        st.markdown("**Risk:** " + risk_value + "/100 · " + level + " — " + risk_detail)
        oracle_row = next((r for r in rows if r["key"] == "oracle"), None)
        if oracle_row and oracle_row["content"]:
            excerpt = oracle_row["content"][:900]
            st.markdown(excerpt + ("\n\n*Full ORACLE output is in the ORACLE tab.*"
                                   if len(oracle_row["content"]) > 900 else ""))
        else:
            st.warning("No ORACLE synthesis was returned for this run.")
        st.markdown("### Per-agent summary")
        for r in rows:
            tools = ", ".join(r["tools"]) if r["tools"] else "no tools recorded"
            st.markdown(f"- **{r['name']}** ({r['role']}) — {r['status'].replace('_', ' ')} · tools: {tools} · {r['snippet'] or 'No output.'}")

    for tab, row in zip(tabs[1:], rows):
        with tab:
            st.markdown(_tab_header_html(row), unsafe_allow_html=True)
            content = row["content"]
            if not content:
                st.warning("This session contains a legacy incomplete response. Run a fresh scan to replace it.")
            elif content.startswith("# Preliminary findings — evidence fallback"):
                st.warning("Model synthesis was unavailable. The content below is a preliminary evidence compilation, not a validated risk assessment.")
                diagnostic = re.search(
                    r"Final language-model synthesis was unavailable:\s*([^\r\n]+)",
                    content,
                )
                if diagnostic:
                    st.caption("SYNTHESIS DIAGNOSTIC · " + diagnostic.group(1)[:320])
                st.markdown(content)
            elif content.startswith("# Agent execution failed"):
                st.error(content)
            else:
                st.markdown(content)

    export = {
        "target": target,
        "target_type": target_type,
        "timestamp": report["timestamp"],
        "risk_score": score,
        "elapsed_seconds": elapsed,
        "model": model_name,
        "findings": results,
    }
    col_json, col_pdf = st.columns(2)
    with col_json:
        st.download_button(
            "Download full report · JSON",
            data=json.dumps(export, indent=2, ensure_ascii=False, default=str),
            file_name="nexus_" + re.sub(r"[^A-Za-z0-9_-]+", "_", target).strip("_") + ".json",
            mime="application/json",
            use_container_width=True,
        )
    with col_pdf:
        try:
            from utils.pdf_generator import generate_pdf

            pdf_bytes = generate_pdf(results)
            st.download_button(
                "Download report · PDF",
                data=pdf_bytes,
                file_name="nexus_" + re.sub(r"[^A-Za-z0-9_-]+", "_", target).strip("_") + ".pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"PDF export unavailable: {type(exc).__name__}: {exc}")
