# services/workspace_openers.py
import importlib, inspect
import streamlit as st
from services.industries import route as industries_route

def open_pm_workspace(industry: str, phase_code: str, proj_type):
    try:
        module_path, entry = industries_route(industry, "projects")
        mod = importlib.import_module(module_path)
        fn = getattr(mod, entry or "render", None) or getattr(mod, "render", None)
        if not callable(fn):
            st.error(f"Workspace module '{module_path}' has no callable render entry.")
            return False
        try:
            params = set(inspect.signature(fn).parameters.keys())
            kwargs = {}
            if "industry" in params:   kwargs["industry"] = industry
            if "I" in params:          kwargs["I"] = industry
            if "phase" in params:      kwargs["phase"] = phase_code
            if "stage" in params:      kwargs["stage"] = phase_code
            if "proj_type" in params:  kwargs["proj_type"] = proj_type
            if "project_type" in params: kwargs["project_type"] = proj_type
            if "st" in params:         kwargs["st"] = st
            fn(**kwargs)
            return True
        except TypeError:
            for args in [
                (),
                (industry,),
                (industry, phase_code),
                (industry, phase_code, proj_type),
            ]:
                try:
                    fn(*args)
                    return True
                except TypeError:
                    continue
            raise
    except Exception as e:
        st.error(f"Workspace load failed for {industry}: {e}")
        return False


# services/workspace_openers.py
import importlib, inspect
import streamlit as st
from services.industries import route as industries_route

def open_ops_hub(industry: str, submode: str) -> bool:
    # 1) Resolve module + entry
    try:
        module_path, entry = industries_route(industry, "ops")
    except Exception as e:
        st.error(f"Ops route error for {industry}: {e}")
        return False

    # 2) Import (with fallback to root-level name)
    try:
        mod = importlib.import_module(module_path)
    except Exception:
        base = module_path.split(".", 1)[-1] if module_path.startswith("workflows.") else module_path
        try:
            mod = importlib.import_module(base)
        except Exception as e2:
            st.error(f"Cannot import Ops module '{module_path}' or fallback '{base}': {e2}")
            return False

    # 3) Choose entry function
    candidates = [
        getattr(mod, entry, None) if entry else None,
        getattr(mod, "render", None),
        getattr(mod, "run", None),
    ]
    sm = (submode or "daily_ops").strip()
    if not any(callable(c) for c in candidates):
        candidates += [
            getattr(mod, sm, None),
            getattr(mod, f"render_{sm}", None),
            getattr(mod, f"{sm}_view", None),
        ]
    fn = next((c for c in candidates if callable(c)), None)
    if not fn:
        st.error(f"Ops Hub '{module_path}' has no callable entry.")
        return False

    # 4) Call with best-possible signature
    try:
        params = set(inspect.signature(fn).parameters.keys())
    except Exception:
        params = set()

    # Prefer kwargs
    if params:
        kwargs = {}
        # IMPORTANT: pass T when accepted so hubs can read ops_mode from it
        if "T" in params:
            kwargs["T"] = {"ops_mode": sm, "industry": industry}
        if "industry" in params: kwargs["industry"] = industry
        if "submode"  in params: kwargs["submode"]  = sm
        if "mode"     in params: kwargs["mode"]     = sm
        if "st"       in params: kwargs["st"]       = st

        try:
            fn(**kwargs)
            st.caption(f"✅ Called: {fn.__name__}(kwargs={list(kwargs.keys())})")
            return True
        except TypeError:
            pass

    # Fallback positional attempts
    for args in [(), (sm,), (industry,), (industry, sm)]:
        try:
            fn(*args)
            st.caption(f"✅ Called: {fn.__name__}{args}")
            return True
        except TypeError:
            continue

    # Last-chance bare call
    try:
        fn()
        st.caption(f"✅ Called: {fn.__name__}()")
        return True
    except Exception as e:
        st.error(f"Ops callable failed: {e}")
        return False
