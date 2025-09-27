# workflows/pm_common/stakeholders.py
from __future__ import annotations
import streamlit as st
from services import stakeholders as _stake
from services import action_center as _ac

_UNIQUE = "rev4_common_stake"

def _chip(label: str) -> None:
    st.markdown(
        f"<span style='padding:2px 8px;border-radius:999px;background:#eef1f5;font-size:12px'>{label}</span>",
        unsafe_allow_html=True,
    )

def render_stakeholders_panel():
    with st.expander("👥 Stakeholder Management", expanded=False):
        rows = _stake.list_stakeholders()
        if rows:
            st.write(f"Total: {len(rows)}")
            for s in rows:
                with st.container():
                    st.markdown(f"**{s['name']}** — {s['role']} @ {s['org']}")
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
                    with col1: _chip(f"Influence {s['influence']}/5")
                    with col2: _chip(f"Interest {s['interest']}/5")
                    with col3: _chip(f"Support {s['support']}")
                    with col4:
                        if st.button("Edit", key=f"{_UNIQUE}_edit_{s['id']}"):
                            st.session_state[f"{_UNIQUE}_edit_sid"] = s["id"]
                    st.divider()
        else:
            st.info("No stakeholders yet. Add one below.")

        # Add / Edit form
        with st.form(f"{_UNIQUE}_form"):
            st.subheader("Add / Edit Stakeholder")
            edit_id = st.session_state.get(f"{_UNIQUE}_edit_sid")
            defaults = _stake.get_stakeholder(edit_id) or {}
            name = st.text_input("Name", value=defaults.get("name", ""))
            org = st.text_input("Organization", value=defaults.get("org", ""))
            role = st.text_input("Role", value=defaults.get("role", ""))
            influence = st.slider("Influence", 1, 5, int(defaults.get("influence", 3)))
            interest = st.slider("Interest", 1, 5, int(defaults.get("interest", 3)))
            support = st.slider("Support (-1..1)", -1, 1, int(defaults.get("support", 0)))
            owner = st.text_input("Owner (user id/email)", value=defaults.get("owner", ""))
            next_touch = st.text_input("Next touch (YYYY-MM-DD)", value=defaults.get("next_touch", ""))
            notes = st.text_area("Notes", value=defaults.get("notes", ""))
            colA, colB = st.columns(2)
            with colA:
                submitted = st.form_submit_button("Save", use_container_width=True)
            with colB:
                delete_btn = st.form_submit_button("Delete", use_container_width=True)

            if submitted:
                payload = dict(
                    name=name, org=org, role=role, influence=influence, interest=interest,
                    support=support, owner=owner, next_touch=next_touch, notes=notes
                )
                if edit_id:
                    _stake.update_stakeholder(edit_id, payload)
                    st.success("Updated.")
                    st.session_state.pop(f"{_UNIQUE}_edit_sid", None)
                else:
                    _stake.add_stakeholder(payload)
                    st.success("Added.")
                st.rerun()

            if delete_btn and edit_id:
                _stake.delete_stakeholder(edit_id)
                st.success("Deleted.")
                st.session_state.pop(f"{_UNIQUE}_edit_sid", None)
                st.rerun()

        # Engagement actions helper
        st.markdown("---")
        colA, colB = st.columns([1, 2])
        with colA:
            make_actions = st.button("Generate Engagement Actions (this week)", key=f"{_UNIQUE}_make_touch_actions")
        with colB:
            st.caption("Creates Action Center items for stakeholders whose 'Next touch' is within the next 7 days.")

        if make_actions:
            from datetime import datetime, timedelta
            today = datetime.today().date()
            horizon = today + timedelta(days=7)
            created = 0
            for s in _stake.list_stakeholders():
                nxt = (s.get("next_touch") or "").strip()
                if not nxt:
                    continue
                try:
                    d = datetime.strptime(nxt, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if today <= d <= horizon:
                    _ac.add_action({
                        "type": "stakeholder_touchpoint",
                        "source_id": s["id"],
                        "title": f"Engage {s['name']} (due {nxt})",
                        "assignee": s.get("owner"),
                        "due": nxt,
                        "status": "open",
                        "notes": s.get("notes", ""),
                    })
                    created += 1
            st.success(f"Created {created} action(s). Check the Action Tracker panel.")
