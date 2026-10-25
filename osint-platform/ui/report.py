"""Report view (moved out of monolithic app.py in v3, logic unchanged).

Risk-score extraction, per-agent findings, JSON + PDF downloads are
identical to v2. PDF mapping fix from v1 is preserved: generate_pdf
receives agent-keyed results (aria/raven/vulcan/cipher/oracle).
"""
import html
import json
import re
from datetime import timezone

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


def render_report(report, profiles, model_name):
    import streamlit as st

    results = report["results"]
    target = report["target"]
    target_type = report["target_type"]
    elapsed = report["elapsed"]
    oracle_text = str(results.get("oracle", ""))
    score = None if _is_legacy_round_limit(oracle_text) else extract_risk_score(oracle_text)
    activity = st.session_state.get("nexus_latest_activity", {})
    completed = sum(
        bool(str(results.get(key, "")).strip())
        and not str(results.get(key, "")).strip().lower().startswith("# agent execution failed")
        and not _is_legacy_round_limit(str(results.get(key, "")))
        for key in AGENT_ORDER
    )
    st.markdown(
        '<div class="section-heading"><div><span class="section-kicker">REPORT</span>'
        '<h2>Intelligence report</h2></div><span>Full findings for every specialist · tools shown by name</span></div>',
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
    for key in AGENT_ORDER:
        agent = profiles[key]
        content = str(results.get(key, "")).strip()
        if _is_legacy_round_limit(content):
            content = ""
        record = activity.get(key, {})
        status = record.get("status", "complete" if content else "error")
        label = f"{agent['name']}  ·  {agent['role']}  ·  {status.replace('_', ' ').upper()}"
        with st.expander(label, expanded=True):
            tool_events = [
                item for item in record.get("activity_log", [])
                if item.get("type") == "tool_call" and item.get("tool_name")
            ]
            tool_names = list(dict.fromkeys(item["tool_name"] for item in tool_events))
            if tool_names:
                st.caption("TOOLS EXECUTED · " + "  /  ".join(tool_names))
            elif key == "oracle":
                st.caption("TOOLS EXECUTED · none (synthesis agent; uses the other specialists’ findings)")
            else:
                st.caption("TOOLS EXECUTED · none recorded")
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
