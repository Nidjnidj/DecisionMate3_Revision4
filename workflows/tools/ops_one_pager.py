# workflows/tools/ops_one_pager.py
from __future__ import annotations

import io
from datetime import datetime
import json
import streamlit as st

# Optional persistence/back
try:
    from data.firestore import load_project_doc, save_project_doc
except Exception:
    load_project_doc = save_project_doc = None
try:
    from services.utils import back_to_hub
except Exception:
    def back_to_hub():
        st.session_state.pop("active_view", None)
        st.session_state.pop("module_info", None)
        st.experimental_rerun()

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    ops_mode = st.session_state.get("ops_mode", "daily_ops")
    return f"{industry}:ops:{ops_mode}"

def render(T=None):
    st.title("🖨️ Ops One-Pager (PDF/TXT)")
    st.caption("Generates a compact one-pager from the consolidated Ops snapshot.")

    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    try:
        industry, _, mode = namespace.split(":")
    except Exception:
        industry, mode = "manufacturing", "daily_ops"
    snap_key = f"{industry}_ops_{mode}"

    snap = {}
    if load_project_doc:
        snap = load_project_doc(username, namespace, project_id, snap_key) or {}

    st.subheader("Snapshot Preview")
    st.json(snap)

    st.divider()
    st.subheader("Export")

    # ---- TXT fallback (always available)
    txt = io.StringIO()
    txt.write(f"Ops One-Pager — {snap_key}\nGenerated: {datetime.utcnow().isoformat()}\n\n")
    for section, payload in (snap.get(mode, {}) or {}).items():
        txt.write(f"[{section.upper()}]\n")
        if isinstance(payload, dict):
            for k, v in payload.items():
                txt.write(f" - {k}: {v}\n")
        else:
            txt.write(json.dumps(payload, indent=2))
        txt.write("\n")
    st.download_button("Download TXT", data=txt.getvalue().encode("utf-8"),
                       file_name="ops_one_pager.txt", mime="text/plain")

    # ---- PDF (best-effort, requires reportlab)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm

        if st.button("Generate PDF"):
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            width, height = A4
            y = height - 2*cm
            c.setFont("Helvetica-Bold", 14)
            c.drawString(2*cm, y, f"Ops One-Pager — {snap_key}"); y -= 0.8*cm
            c.setFont("Helvetica", 9)
            c.drawString(2*cm, y, f"Generated: {datetime.utcnow().isoformat()}"); y -= 0.8*cm

            data = snap.get(mode, {}) or {}
            for section, payload in data.items():
                c.setFont("Helvetica-Bold", 11)
                c.drawString(2*cm, y, section.upper()); y -= 0.6*cm
                c.setFont("Helvetica", 9)
                if isinstance(payload, dict):
                    for k, v in payload.items():
                        line = f"- {k}: {v}"
                        if y < 2*cm:
                            c.showPage(); y = height - 2*cm
                        c.drawString(2.2*cm, y, line); y -= 0.5*cm
                else:
                    text = json.dumps(payload, indent=2)
                    for line in text.splitlines():
                        if y < 2*cm:
                            c.showPage(); y = height - 2*cm
                        c.drawString(2.2*cm, y, line[:95]); y -= 0.45*cm
                y -= 0.3*cm

            c.save()
            st.download_button("Download PDF", data=buf.getvalue(),
                               file_name="ops_one_pager.pdf", mime="application/pdf")
    except Exception:
        st.caption("PDF generation requires `reportlab`. If missing, use TXT export above.")
    st.divider()
    if st.button("↩ Back to Ops Hub", key="ops_one_pager_back"):
        back_to_hub()
