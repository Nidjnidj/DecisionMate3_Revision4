# services/utils.py
import streamlit as st
import time

def _compute_namespace(industry: str) -> str:
    mode = st.session_state.get("mode", "projects")
    if mode == "ops":
        # prefer a page-local override if provided
        effective_ops = (
            st.session_state.get("ops_mode_override")
            or st.session_state.get("ops_mode", "daily_ops")
        )
        return f"{industry}:ops:{effective_ops}"
    return f"{industry}:projects"

def _log_recent_tool(title: str, module_path: str, entry: str, context: dict) -> None:
    try:
        from data.firestore import load_project_doc, save_project_doc
        username = st.session_state.get("username", "Guest")
        project_id = st.session_state.get("active_project_id")
        industry = st.session_state.get("industry", "oil_gas")
        namespace = _compute_namespace(industry)
        if not project_id:
            return
        doc_key = "recent_tools"
        payload = load_project_doc(username, namespace, project_id, doc_key) or {"items": []}
        items = payload.get("items", [])
        items.append({
            "ts": time.time(),
            "title": title,
            "module_path": module_path,
            "entry": entry,
            "context": context,
        })
        payload["items"] = items[-30:]
        save_project_doc(username, namespace, project_id, doc_key, payload)
    except Exception:
        pass

def go_to_module(module_path: str, entry: str, context: dict) -> None:
    # optional: title can be passed via context["tool_title"]
    title = context.get("tool_title", module_path.split(".")[-1])

    # NEW: honor page-local ops mode (do NOT touch 'ops_mode')
    if context.get("ops_mode"):
        st.session_state["ops_mode_override"] = context["ops_mode"]

    _log_recent_tool(title, module_path, entry, context)


    # Remember the currently opened tool (so the save shim can mark completion)
    st.session_state["__current_tool"] = {"module_path": module_path, "entry": entry, "title": title}

    st.session_state.active_view = "module"
    st.session_state.module_info = {"module_path": module_path, "entry": entry, "context": context}
    try:
        st.query_params.from_dict({"view": "module"})
    except Exception:
        st.query_params["view"] = "module"
    st.rerun()

def back_to_hub() -> None:
    # NEW: clear any page-local override
    st.session_state.pop("ops_mode_override", None)

    st.session_state.active_view = None
    st.session_state.module_info = None

    try:
        st.query_params.from_dict({})
    except Exception:
        try:
            st.query_params.clear()
        except Exception:
            pass
    st.rerun()
