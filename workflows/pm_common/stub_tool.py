# workflows/pm_common/stub_tool.py
from __future__ import annotations
import io
from typing import Any, Callable, Dict, List, Optional, Tuple
import streamlit as st
from services.pm_bridge import save_stage, load_stage

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

Field = Tuple[str, Any, str]  # (key, default, "int|float|text")


def _num(v, typ):
    try:
        return int(v) if typ == "int" else float(v)
    except Exception:
        return 0


def _draw_chart(data: Dict[str, Any]):
    if not plt:
        return
    # Plot numeric fields only
    nums = {k: v for k, v in data.items() if isinstance(v, (int, float))}
    if not nums:
        return
    fig = plt.figure()
    plt.bar(list(nums.keys()), list(nums.values()))
    plt.xticks(rotation=20, ha="right")
    plt.title("Snapshot")
    st.pyplot(fig, clear_figure=True)


def _csv_download_button(name: str, payload: Dict[str, Any], key: str):
    buf = io.StringIO()
    buf.write("key,value\n")
    for k, v in payload.items():
        buf.write(f"{k},{v}\n")
    st.download_button(
        "Download CSV",
        data=buf.getvalue().encode(),
        file_name=f"{name.replace(' ', '_').lower()}_snapshot.csv",
        mime="text/csv",
        key=f"{key}_csv",
    )


def make_run(
    tool_title: str,
    fel_stage: str,
    fields: Optional[List[Field]] = None,
    loads_from: Optional[str] = None,
    compute: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
):
    """Return a run(**kwargs) callable for a minimal tool UI.
    - fields: list of (key, default, type)
    - loads_from: prior stage to prefill defaults
    - compute: optional function(prev_payload) -> dict of derived outputs (also saved)
    """
    def run(**kwargs):
        key_prefix = kwargs.get("key", tool_title.replace(" ", "_"))
        st.subheader(tool_title)

        pre = load_stage(loads_from, {}).get("payload", {}) if loads_from else {}
        st.caption("Prefill from prior stage:" if pre else "No prior data found")
        if pre:
            st.json(pre, expanded=False)

        payload: Dict[str, Any] = {}

        # Input fields
        if fields:
            cols = st.columns(max(2, min(4, len(fields))))
            for idx, (k, default, typ) in enumerate(fields):
                val_default = pre.get(k, default)
                with cols[idx % len(cols)]:
                    if typ == "int":
                        v = st.number_input(k, value=int(val_default or 0), step=1, key=f"{key_prefix}_{k}")
                    elif typ == "float":
                        v = st.number_input(k, value=float(val_default or 0.0), step=1.0, key=f"{key_prefix}_{k}")
                    else:
                        v = st.text_input(k, value=str(val_default or ""), key=f"{key_prefix}_{k}")
                payload[k] = v

        # Derived block
        derived = {}
        if callable(compute):
            try:
                derived = compute(pre if pre else payload)
            except Exception as e:
                st.warning(f"Compute failed: {e}")
        if derived:
            st.markdown("**Derived**")
            c2 = st.columns(len(derived))
            for i, (k, v) in enumerate(derived.items()):
                with c2[i % len(c2)]:
                    st.metric(k, v)
            payload.update(derived)

        # Save + CSV
        save_cols = st.columns(2)
        with save_cols[0]:
            if st.button("Save snapshot", key=f"{key_prefix}_save"):
                save_stage(fel_stage, payload)
                st.success(f"Saved to {fel_stage}")
        with save_cols[1]:
            _csv_download_button(tool_title, payload, key_prefix)

        # Tiny chart
        _draw_chart(payload)

    return run