# workflows/pm_common/moc.py
from __future__ import annotations
import streamlit as st
from services import moc as _moc

_UNIQUE = "rev4_common_moc"

IMPACT_CHOICES = ["Scope", "Schedule", "Cost", "Quality", "Safety", "Other"]
STATUS_CHOICES = ["open", "approved", "rejected", "withdrawn"]

def render_moc_panel():
    with st.expander("🔄 Management of Change (MOC)", expanded=False):
        rows = _moc.list_moc()
        if rows:
            st.write(f"Total: {len(rows)}")
            for r in rows:
                with st.container(border=True):
                    st.markdown(f"**{r['title']}** — status: `{r['status']}`")
                    st.caption(f"Requester: {r.get('requester','')} · Approver: {r.get('approver','')}")
                    st.caption(f"Impacts: {', '.join(r.get('impacts', [])) or '—'}")
                    if r.get("description"):
                        st.write(r["description"])
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("Edit", key=f"{_UNIQUE}_edit_{r['id']}"):
                            st.session_state[f"{_UNIQUE}_edit_id"] = r["id"]
                    with col2:
                        if st.button("Delete", key=f"{_UNIQUE}_del_{r['id']}"):
                            _moc.delete_moc(r["id"])
                            st.rerun()
        else:
            st.info("No MOC requests yet. Add one below.")

        with st.form(f"{_UNIQUE}_form"):
            st.subheader("Add / Edit MOC")
            edit_id = st.session_state.get(f"{_UNIQUE}_edit_id")
            defaults = _moc.get_moc(edit_id) or {}
            title = st.text_input("Title", value=defaults.get("title",""))
            description = st.text_area("Description", value=defaults.get("description",""))
            impacts = st.multiselect("Impacts", IMPACT_CHOICES, default=defaults.get("impacts", []))
            requester = st.text_input("Requester", value=defaults.get("requester",""))
            approver = st.text_input("Approver", value=defaults.get("approver",""))
            status = st.selectbox("Status", STATUS_CHOICES, index=max(0, STATUS_CHOICES.index(defaults.get("status","open"))))
            links = st.text_input("Linked artifact IDs (comma-separated)", value=",".join(defaults.get("links", [])))

            colA, colB = st.columns(2)
            with colA:
                submitted = st.form_submit_button("Save", use_container_width=True)
            with colB:
                cancel = st.form_submit_button("Cancel edit", use_container_width=True)

            if submitted:
                payload = dict(
                    title=title,
                    description=description,
                    impacts=impacts,
                    requester=requester,
                    approver=approver,
                    status=status,
                    links=[s.strip() for s in links.split(",") if s.strip()],
                )
                if edit_id:
                    _moc.update_moc(edit_id, payload)
                    st.success("Updated.")
                    st.session_state.pop(f"{_UNIQUE}_edit_id", None)
                else:
                    _moc.add_moc(payload)
                    st.success("Added.")
                st.rerun()

            if cancel and edit_id:
                st.session_state.pop(f"{_UNIQUE}_edit_id", None)
                st.info("Edit cancelled.")
