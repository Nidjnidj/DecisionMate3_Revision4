# frontdoor.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

# ---------- Page config (must be one of the first Streamlit calls) ----------

# ---- Optional deps (handled gracefully) ----
try:
    from streamlit_lottie import st_lottie  # pip install streamlit-lottie
    LOTTIE_OK = True
except Exception:
    LOTTIE_OK = False

# --- Auth completely disabled (guest mode only) ---
FIREBASE_OK = False  # hard disable
# (Optional) if you have firebase_db imports elsewhere, keep the try/except but don't use it.
# try:
#     import firebase_db as fdb
# except Exception:
#     fdb = None


# ========= Utility =========
ANIM_H = 180  # unified desktop/tablet animation height
MOBILE_ANIM_H = 150

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

def asset_path(*parts: str) -> str:
    """Resolve assets from project root first, then /mnt/data fallback."""
    p1 = Path.cwd().joinpath(*parts)
    if p1.exists():
        return str(p1)
    if len(parts) == 1:
        p2 = Path("/mnt/data").joinpath(parts[0])
        if p2.exists():
            return str(p2)
    # last-resort: name only under /mnt/data
    return str(Path("/mnt/data").joinpath(parts[-1]))

def _load_lottie_raw(fname: str) -> Optional[dict]:
    for candidate in [asset_path("animations", fname), asset_path(fname)]:
        try:
            p = Path(candidate)
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None

@st.cache_data(show_spinner=False)
def load_lottie_cached(fname: str) -> Optional[dict]:
    return _load_lottie_raw(fname)

def _anim_h() -> int:
    return MOBILE_ANIM_H if st.session_state.get("is_mobile") else ANIM_H

# ========= Nav State =========
def _init_state():
    st.session_state.setdefault("nav_open", False)
    st.session_state.setdefault("current_page", "Home")
    st.session_state.setdefault("theme", "light")


# ========= Theme / CSS =========
def _theme_css():
    mode = st.session_state.get("theme", "light")
    PAL = {
        "light": {
            "bg": "#F7FAFF", "bg2": "#FFFFFF", "card": "#FFFFFFCC", "text": "#0F172A",
            "muted": "#667085", "accent": "#2563EB", "accent2": "#7C3AED",
            "border": "#E6EAF2", "shadow": "0 8px 24px rgba(16, 24, 40, 0.06)",
            "hero_grad": "linear-gradient(135deg, rgba(37,99,235,.10), rgba(124,58,237,.10))",
        },
        "dark": {
            "bg": "#0B1220", "bg2": "#121A2B", "card": "rgba(255,255,255,0.06)", "text": "#E5E7EB",
            "muted": "#9AA0A6", "accent": "#3B82F6", "accent2": "#A78BFA",
            "border": "rgba(255,255,255,0.14)", "shadow": "0 8px 24px rgba(0,0,0,0.45)",
            "hero_grad": "linear-gradient(135deg, rgba(37,99,235,.14), rgba(124,58,237,.14))",
        },
    }[mode]

    # 1) First style block: only inject CSS variables via f-string (no raw braces besides :root)
    st.markdown(
        f"""
<style>
  /* Inter font */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

  :root {{
    --dm-bg: {PAL["bg"]};
    --dm-bg-2: {PAL["bg2"]};
    --dm-card: {PAL["card"]};
    --dm-text: {PAL["text"]};
    --dm-muted: {PAL["muted"]};
    --dm-accent: {PAL["accent"]};
    --dm-accent-2: {PAL["accent2"]};
    --dm-border: {PAL["border"]};
    --dm-shadow: {PAL["shadow"]};
    --dm-hero-grad: {PAL["hero_grad"]};
    --dm-br: 16px;
  }}
</style>
""",
        unsafe_allow_html=True,
    )

    # 2) Second style block: plain string CSS (no f-string -> safe braces)
    st.markdown(
        """
<style>
  html, body, [class*="css"] { font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
  body, .block-container { background: var(--dm-bg); }
  .block-container { padding-top:.8rem; padding-bottom:2rem; }

  section[data-testid="stSidebar"] > div {
    background:#F3F6FC !important; border-right:1px solid var(--dm-border);
  }
  /* Center the app icon in the sidebar */
  section[data-testid="stSidebar"] img { display:block; margin:8px auto; }

  /* Helper class to center content inside cards */
  .dm-center { display:flex; justify-content:center; align-items:center; }

  /* Slightly larger brand logo for better balance */
  .brand-logo { width:80px; height:80px; border-radius:10px; object-fit:contain; }
  @media (max-width: 768px) {
    .brand-logo { width:64px; height:64px; }
  }

  /* HERO */
  .dm-hero {
    position:relative; overflow:hidden; text-align:center; padding:22px 18px; border-radius:20px;
    background:var(--dm-hero-grad); border:1px solid var(--dm-border);
    color:var(--dm-text); box-shadow:var(--dm-shadow); margin-bottom:12px;
  }
  .dm-hero::before, .dm-hero::after {
    content:""; position:absolute; width:220px; height:220px; filter:blur(50px); z-index:-1; opacity:.35; border-radius:50%;
  }
  .dm-hero::before{ left:10%; top:-60px; background:#c7d2fe; }
  .dm-hero::after{ right:8%; top:-40px; background:#e9d5ff; }
  .dm-title { font-size:36px; font-weight:800; letter-spacing:.2px; margin:0; }
  .dm-sub { color:var(--dm-muted); margin-top:.25rem; }

  .dm-badge {
    display:inline-flex; align-items:center; gap:10px; padding:6px 10px;
    border:1px solid var(--dm-border); border-radius:999px; background:var(--dm-bg-2);
  }

  /* Chips / Cards */
  .dm-chip {
    background:var(--dm-bg-2); color:var(--dm-text); border:1px solid var(--dm-border);
    border-radius:14px; padding:12px 14px; box-shadow:var(--dm-shadow);
    transition: transform .12s ease, box-shadow .12s ease;
  }
  .dm-card {
    background:var(--dm-card); backdrop-filter:blur(6px);
    border:1px solid var(--dm-border); border-radius:var(--dm-br); padding:16px; box-shadow:var(--dm-shadow);
  }

  .dm-note { color:var(--dm-muted); font-size:13px; }

  /* Grids */
  .dm-grid-3 { display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; }
  .dm-grid-2 { display:grid; grid-template-columns: repeat(2, 1fr); gap:12px; }
  @media (max-width: 1200px) {
    .dm-grid-3 { grid-template-columns:1fr; }
    .dm-grid-2 { grid-template-columns:1fr; }
  }

  /* Buttons */
  .dm-btn {
    background:var(--dm-accent); color:#fff; border:none; border-radius:12px;
    padding:10px 14px; width:100%; font-weight:600; cursor:pointer;
    transition: transform .12s ease, box-shadow .12s ease;
  }
  .dm-ghost {
    background:transparent; border:1px solid var(--dm-border); color:var(--dm-text);
    border-radius:12px; padding:10px 14px; width:100%; font-weight:600; cursor:pointer;
  }
  .dm-btn:hover, .dm-chip:hover { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(16,24,40,.08); }

  /* Small brand logo (Nijat) */
  .brand-logo { width:64px; height:64px; border-radius:10px; object-fit:contain; }

  /* --- Mobile tuning (Material-ish) --- */
  @media (max-width: 768px) {
    .dm-title { font-size: 26px; }
    .dm-hero { padding: 16px 12px; border-radius: 16px; }
    .dm-card { padding: 12px; border-radius: 14px; }
    .dm-chip { padding: 10px 12px; border-radius: 12px; }
    button[kind="secondary"], button[kind="primary"],
    .dm-btn, .dm-ghost { min-height: 48px; border-radius: 14px; font-size: 16px; }
    .dm-grid-3, .dm-grid-2 { grid-template-columns: 1fr !important; gap: 10px; }
    section[data-testid="stSidebar"] img { max-width: 60%; }
    .dm-card, .dm-chip, .dm-hero { box-shadow: 0 4px 12px rgba(16,24,40,.06); }
  }
</style>
""",
        unsafe_allow_html=True,
    )


# ========= Resume pointer =========
def _save_resume_pointer(uid: str, project_id: Optional[str], phase_id: Optional[str]):
    if not (FIREBASE_OK and uid):
        return
    try:
        fdb.save_user_state(uid=uid, data={"last_project_id": project_id, "last_phase_id": phase_id})  # noqa: F821
    except Exception:
        pass

def _load_resume_pointer(uid: str) -> Tuple[Optional[str], Optional[str]]:
    if not (FIREBASE_OK and uid):
        return (None, None)
    try:
        data = fdb.load_user_state(uid=uid) or {}  # noqa: F821
        return data.get("last_project_id"), data.get("last_phase_id")
    except Exception:
        return (None, None)


# ========= Sections =========
def _hero():
    # Header banner (kept)
    st.markdown(
        """
      <div class='dm-hero'>
        <div class='dm-title'>DecisionMate</div>
        <div class='dm-sub'>Smarter Decisions. Faster Outcomes. Resume exactly where you left off.</div>
      </div>
    """,
        unsafe_allow_html=True,
    )

    # Row under header: left = centered badge, right = centered animation
    left, right = st.columns([2, 1])

    # ---------- LEFT: centered badge ----------
    with left:
        brand_src = asset_path("nijat_logo.png")
        if not Path(brand_src).exists():
            brand_src = asset_path("decisionmate.png")

        # Card shell
        st.markdown("<div class='dm-card'>", unsafe_allow_html=True)

        # Center the whole badge using side spacers, then logo + text inside
        spacerL, mid, spacerR = st.columns([1, 4, 1])  # mid is centered area
        with mid:
            lcol, rcol = st.columns([0.22, 0.78])      # logo + text
            with lcol:
                img_w = 64 if st.session_state.get("is_mobile") else 170
                st.image(brand_src, width=img_w)
            with rcol:
                st.markdown(
                    "**Decision <span style='font-weight:900;'>Mate</span>**",
                    unsafe_allow_html=True,
                )
                st.caption("Decision Intelligence Toolkit · by Nijat Isgandarov")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- RIGHT: centered animation ----------
    with right:
        if LOTTIE_OK:
            anim = load_lottie_cached("business_team.json")
            if anim:
                # wrap to horizontally center the lottie
                cL, cM, cR = st.columns([1, 2, 1])
                with cM:
                    st_lottie(anim, height=_anim_h(), key="hero_anim")
        else:
            cL, cM, cR = st.columns([1, 2, 1])
            with cM:
                st.image(asset_path("decisionmate.png"), width=70)

    # ---- Open/Close nav button (state-driven, no JS) ----
    with st.container():
        if st.button(
            "☰ Open navigation" if not st.session_state["nav_open"] else "✖ Close navigation",
            use_container_width=True,
            key="btn_nav_toggle",
        ):
            st.session_state["nav_open"] = not st.session_state["nav_open"]
            _rerun()

def _announcement(text="✨ Rev4 adds AI Benchmarking, polished front door, and guest mode!"):
    st.markdown(
        f"""
    <div class='dm-card' style='margin-top:8px;background:linear-gradient(90deg,#eef4ff,#f6f3ff);'>
      <div style='display:flex;gap:10px;align-items:center'>
        <span>🆕</span><div class='dm-note'>{text}</div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

def _resume_card():
    uid = st.session_state.get("uid")
    if not uid:
        return
    p, ph = _load_resume_pointer(uid)
    if not (p or ph):
        return
    with st.container():
        cols = st.columns([0.8, 0.2])
        with cols[0]:
            st.markdown(
                f"""
                <div class='dm-card'>
                  <div style='font-weight:700'>Continue where you left off</div>
                  <div class='dm-note'>Project: <b>{p or "—"}</b> · Phase: <b>{ph or "—"}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with cols[1]:
            if st.button("▶ Resume", use_container_width=True, key="resume_btn"):
                if p:
                    st.session_state["current_project_id"] = p
                if ph:
                    st.session_state["current_phase_id"] = ph
                st.session_state["auth_state"] = "user"
                _rerun()

def _info_three_cards():
    st.markdown("<div class='dm-grid-3'>", unsafe_allow_html=True)

    st.markdown(
        """
      <div class='dm-card'>
        <h4>Why DecisionMate?</h4>
        <p class='dm-note'>
          Complex projects run across scattered tools (Excel, P6, Word, Email).
          DecisionMate centralizes governance, analytics, and AI into one workspace—
          so teams move faster with fewer handoffs.
        </p>
        <ul class='dm-note'>
          <li>One place for artifacts, approvals, KPIs, and risks.</li>
          <li>AI summaries & decision support on top of your data.</li>
          <li>Consistent stage-gate execution across industries.</li>
        </ul>
      </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
      <div class='dm-card'>
        <h4>Problems We Solve</h4>
        <ul class='dm-note'>
          <li><b>Fragmentation</b>: cost, schedule, risks spread across apps.</li>
          <li><b>Slow gates</b>: unclear deliverables & review loops.</li>
          <li><b>No benchmarks</b>: hard to compare with similar projects.</li>
          <li><b>Poor visibility</b>: stakeholders lack live KPIs.</li>
        </ul>
        <p class='dm-note'>DecisionMate links Engineering → Schedule → Cost and keeps governance clear.</p>
      </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
      <div class='dm-card'>
        <h4>What You Can Do</h4>
        <ul class='dm-note'>
          <li>Run the <b>AI Optimizer</b> for cost/schedule/economics.</li>
          <li>Use <b>AI Benchmarking</b> to compare scope, cost, durations.</li>
          <li>See <b>PM Analytics</b>: KPIs, milestones, risks, actions.</li>
          <li>Create & export artifacts (DOCX / PDF / Excel).</li>
          <li>Work in hubs for Oil & Gas, IT, Aerospace, Construction, and more.</li>
        </ul>
      </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

def _industries_strip():
    st.markdown(
        """
    <div class='dm-card'>
      <div class='dm-note' style='margin-bottom:6px'>Supported industries</div>
      <div style='display:flex;flex-wrap:wrap;gap:8px'>
        <span class='dm-chip'>🏭 Manufacturing</span>
        <span class='dm-chip'>🛢️ Oil & Gas</span>
        <span class='dm-chip'>🛰️ Aerospace</span>
        <span class='dm-chip'>🏗️ Construction</span>
        <span class='dm-chip'>💻 IT</span>
        <span class='dm-chip'>🏥 Healthcare</span>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

def _feature_chips():
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🚀 AI Optimizer", use_container_width=True):
            try:
                from ai import ai_optimizer
                ai_optimizer.render()
                st.stop()
            except Exception:
                st.warning("AI Optimizer module not available.")
    with c2:
        if st.button("📊 AI Benchmarking", use_container_width=True):
            try:
                from ai import ai_benchmarking
                ai_benchmarking.render()
                st.stop()
            except Exception:
                st.warning("AI Benchmarking module not available.")
    with c3:
        if st.button("📈 PM Analytics", use_container_width=True):
            try:
                from ai import ai_pm_analytics
                ai_pm_analytics.render()
                st.stop()
            except Exception:
                st.warning("AI PM Analytics module not available.")

def _login_block() -> Tuple[Optional[str], Optional[str], bool]:
    st.subheader("Sign in")
    with st.form("dm_login", clear_on_submit=False):
        email = st.text_input("Email", key="dm_login_email")
        password = st.text_input("Password", type="password", key="dm_login_pass")
        _ = st.checkbox("Remember me on this device", value=True, key="dm_remember")
        submitted = st.form_submit_button("Sign in", use_container_width=True)
        st.caption(
            "By signing in you agree to our Terms and Privacy Policy. "
            "To delete your account/data, contact support@your-domain.com."
        )
    return email, password, submitted

def _guest_block() -> bool:
    st.markdown("### Or try without login")
    g_left, g_right = st.columns([0.6, 0.4])
    clicked = False
    with g_left:
        if st.button("Continue as Guest", use_container_width=True, key="dm_guest_btn"):
            clicked = True
    with g_right:
        if LOTTIE_OK:
            typing = load_lottie_cached("cat_typing.json")  # distinct: guest
            if typing:
                st_lottie(typing, height=_anim_h(), key="dm_cat_typing")
    return clicked

def _what_is_dm(info_col):
    with info_col:
        st.markdown("<div class='dm-card'>", unsafe_allow_html=True)
        st.markdown("<h4>What is DecisionMate?</h4>", unsafe_allow_html=True)
        st.markdown(
            """
          <p class='dm-note'>
            A unified decision-support platform for engineering & operations.
            Plug your artifacts, get AI-powered summaries, risks, benchmarking, and instant business case drafts.
          </p>
          <ul class='dm-note'>
            <li>Industry hubs: Oil & Gas, Manufacturing, IT, Aerospace, Construction.</li>
            <li>FEL governance with deliverables, reviews, and approvals.</li>
            <li>Exports: DOCX / PDF / Excel · Integrations: Firebase.</li>
          </ul>
        """,
            unsafe_allow_html=True,
        )
        if LOTTIE_OK:
            viz = load_lottie_cached("data_analysis.json")  # distinct: right info
            if viz:
                st_lottie(viz, height=_anim_h(), key="dm_info_anim")
        st.markdown("</div>", unsafe_allow_html=True)

def _guest_tip():
    if st.session_state.get("auth_state") == "guest":
        st.info("You're exploring as a guest. Sign in anytime to save your work and resume later.")

def _footer():
    st.markdown(
        """
    <div class='dm-note' style='text-align:center;margin-top:10px'>
      <a href='https://YOUR-DOMAIN/docs' target='_blank' style='text-decoration:none;color:inherit'>Docs</a> ·
      <a href='https://YOUR-DOMAIN/privacy' target='_blank' style='text-decoration:none;color:inherit'>Privacy</a> ·
      <a href='mailto:support@your-domain.com' style='text-decoration:none;color:inherit'>Contact</a>
      <br/>© 2025 DecisionMate. Built by Nijat Isgandarov.
    </div>
    """,
        unsafe_allow_html=True,
    )


# ========= Entry =========
def render_frontdoor():

    _init_state()   # <-- initialize nav + page state early
    _theme_css()

    if "is_mobile" not in st.session_state:
        st.session_state["is_mobile"] = False  # simple default

    # Sidebar branding + NAV
    with st.sidebar:
        st.image(asset_path("decisionmate.png"), caption="DecisionMate", use_container_width=True)
        st.markdown("<div class='dm-note'>Decision Intelligence Toolkit</div>", unsafe_allow_html=True)

        # Actual nav (renders only when nav_open = True)
        if st.session_state["nav_open"]:
            page = st.radio(
                "Go to",
                ["Home", "AI Optimizer", "AI Benchmarking", "PM Analytics", "Settings"],
                index=["Home", "AI Optimizer", "AI Benchmarking", "PM Analytics", "Settings"]
                      .index(st.session_state["current_page"]),
                key="nav_radio_main",
            )
            if page != st.session_state["current_page"]:
                st.session_state["current_page"] = page
                _rerun()
        else:
            st.caption("Use “☰ Open navigation” to access modules.")

    # ===== Inline Navigation Fallback (appears in main area when nav_open=True) =====
    if st.session_state.get("nav_open"):
        st.markdown("<div class='dm-card'>", unsafe_allow_html=True)
        st.markdown("#### Navigation", unsafe_allow_html=True)
        page_inline = st.radio(
            "Go to",
            ["Home", "AI Optimizer", "AI Benchmarking", "PM Analytics", "Settings"],
            index=["Home", "AI Optimizer", "AI Benchmarking", "PM Analytics", "Settings"]
                  .index(st.session_state["current_page"]),
            key="nav_radio_inline",
            horizontal=False,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        if page_inline != st.session_state["current_page"]:
            st.session_state["current_page"] = page_inline
            _rerun()

    # HERO + info + quick access
    _hero()
    _resume_card()
    _announcement()
    _info_three_cards()
    _industries_strip()
    _feature_chips()
    st.markdown("")

    # Guest-only mode (no sign-in at all)
    auth_col, info_col = st.columns([1, 1])
    with auth_col:
        st.subheader("Try DecisionMate")
        st.info("Sign-in is disabled in this build. Explore instantly in Guest mode.")
        c1, c2 = st.columns([0.6, 0.4])
        with c1:
            if st.button("Continue as Guest", use_container_width=True, key="dm_guest_only"):
                st.session_state["auth_state"] = "guest"
                st.session_state.setdefault("current_project_id", "P-DEMO")
                st.session_state.setdefault("current_phase_id", "PH-FEL1")
                st.success("Guest mode: your work won’t be saved.")
                _rerun()
        with c2:
            # cute typing cat if you want to keep the animation
            if LOTTIE_OK:
                typing = load_lottie_cached("cat_typing.json")
                if typing:
                    st_lottie(typing, height=_anim_h(), key="dm_cat_guest_only")
    _what_is_dm(info_col)

    # --- Simple router (keeps front door intact) ---
    page = st.session_state["current_page"]
    if page == "AI Optimizer":
        try:
            from ai import ai_optimizer
            ai_optimizer.render()
            st.stop()
        except Exception:
            st.warning("AI Optimizer module not available.")
    elif page == "AI Benchmarking":
        try:
            from ai import ai_benchmarking
            ai_benchmarking.render()
            st.stop()
        except Exception:
            st.warning("AI Benchmarking module not available.")
    elif page == "PM Analytics":
        try:
            from ai import ai_pm_analytics
            ai_pm_analytics.render()
            st.stop()
        except Exception:
            st.warning("AI PM Analytics module not available.")
    # Home / Settings: remain on the front door for now (optional to implement)

    # Footer + tips
    _guest_tip()
    st.markdown("")
    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("📘 Docs / Learn More", use_container_width=True, key="dm_docs"):
            st.toast("Docs section coming soon.")
    with colB:
        if st.button("🌙 Toggle Theme", use_container_width=True, key="dm_theme"):
            st.session_state["theme"] = "dark" if st.session_state.get("theme") != "dark" else "light"
            _rerun()
    with colC:
        if st.button("🚀 Continue", use_container_width=True, key="dm_continue"):
            uid = st.session_state.get("uid")
            if uid:
                p, ph = _load_resume_pointer(uid)
                if p:
                    st.session_state["current_project_id"] = p
                if ph:
                    st.session_state["current_phase_id"] = ph
            st.session_state["auth_state"] = st.session_state.get("auth_state") or "guest"
            _rerun()

    _footer()
