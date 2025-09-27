import streamlit as st
import io
import math
import numpy as np
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Tuple
from modules._common import SUBSURFACE_DELIV_BY_STAGE as DELIV_BY_STAGE
from modules._common import _ensure_deliverable, _mark_deliverable, _set_artifact_status

# Persist artifact & emit events
from artifact_registry import save_artifact  # :contentReference[oaicite:3]{index=3}


# --- import shim so this file works both as a package and as a script ---
import sys, pathlib
_THIS_DIR = pathlib.Path(__file__).resolve().parent       # .../DecisionMate3_Revision4/modules
_ROOT_DIR = _THIS_DIR.parent                               # .../DecisionMate3_Revision4
for p in (str(_THIS_DIR), str(_ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Try package import first; fall back to sibling import if run as a script
try:
    from modules._common import (
        SUBSURFACE_DELIV_BY_STAGE as DELIV_BY_STAGE,
        _ensure_deliverable, _mark_deliverable, _set_artifact_status,
    )
except Exception:
    from _common import (  # type: ignore
        SUBSURFACE_DELIV_BY_STAGE as DELIV_BY_STAGE,
        _ensure_deliverable, _mark_deliverable, _set_artifact_status,
    )

ARTIFACT = "Reservoir_Profiles"
# --- Composition helpers (add near other imports) ---
DEFAULT_GAS = [
    {"component": "N2",  "z": 0.01},
    {"component": "CO2", "z": 0.01},
    {"component": "H2S", "z": 0.00},
    {"component": "C1",  "z": 0.74},
    {"component": "C2",  "z": 0.08},
    {"component": "C3",  "z": 0.07},
    {"component": "iC4", "z": 0.02},
    {"component": "nC4", "z": 0.02},
    {"component": "iC5", "z": 0.02},
    {"component": "nC5", "z": 0.02},
    {"component": "C6+", "z": 0.01},
]

DEFAULT_OIL_PSEUDO = [
    {"component": "C1",  "z": 0.05},
    {"component": "C2",  "z": 0.03},
    {"component": "C3",  "z": 0.05},
    {"component": "iC4", "z": 0.03},
    {"component": "nC4", "z": 0.04},
    {"component": "iC5", "z": 0.05},
    {"component": "nC5", "z": 0.05},
    {"component": "C6+", "z": 0.70},
]

DEFAULT_INJ_GAS = [
    {"component": "N2",  "z": 0.00},
    {"component": "CO2", "z": 0.00},
    {"component": "H2S", "z": 0.00},
    {"component": "C1",  "z": 0.90},
    {"component": "C2",  "z": 0.05},
    {"component": "C3",  "z": 0.03},
    {"component": "C4+", "z": 0.02},  # if you prefer, split to iC4/nC4/…
]

def _normalize_z(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "z" not in df.columns:
        df["z"] = 0.0
    z = pd.to_numeric(df["z"], errors="coerce").fillna(0.0).clip(lower=0.0)
    s = z.sum()
    if s > 0:
        z = z / s
    df["z"] = z
    return df

def _z_sum_ok(df: pd.DataFrame, tol: float = 1e-3) -> bool:
    try:
        s = pd.to_numeric(df["z"], errors="coerce").fillna(0.0).sum()
        return abs(s - 1.0) <= tol
    except Exception:
        return False


# ---------- Small utils ----------
def _to_date(x) -> date:
    if isinstance(x, (datetime, date)):
        return x.date() if isinstance(x, datetime) else x
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(str(x), fmt).date()
        except Exception:
            pass
    return None

def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)

def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "date" not in df.columns:
        raise ValueError("CSV must have a 'date' column")
    dt = pd.to_datetime(df["date"], errors="coerce")
    if dt.isna().any():
        raise ValueError("Could not parse some dates; expected YYYY-MM or YYYY-MM-DD")
    df.index = dt
    df.drop(columns=["date"], inplace=True)
    df = df.sort_index()
    return df


# ---------- Arps decline ----------
def arps_rate(qi: float, Di: float, b: float, t_years: np.ndarray) -> np.ndarray:
    if abs(b) < 1e-6:
        return qi * np.exp(-Di * t_years)
    return qi / np.power(1.0 + b * Di * t_years, 1.0 / b)

def _fit_exp(dates: List[date], q: np.ndarray) -> Tuple[float, float]:
    mask = q > 0
    if mask.sum() < 3:
        return float(q[mask][0] if mask.any() else 1000.0), 0.8
    q = q[mask]
    dts = np.array([dates[i] for i, m in enumerate(mask) if m])
    t0 = dts[0]
    t_years = np.array([(_months_between(t0, d) / 12.0) for d in dts], dtype=float)
    lnq = np.log(q)
    A = np.vstack([np.ones_like(t_years), -t_years]).T
    x, *_ = np.linalg.lstsq(A, lnq, rcond=None)
    qi = float(np.exp(x[0])); Di = float(x[1])
    return qi, Di

def fit_arps(dates: List[date], q: np.ndarray, prefer_hyperbolic: bool = True) -> Tuple[float, float, float]:
    qi_exp, Di_exp = _fit_exp(dates, q)
    best_qi, best_Di, best_b = qi_exp, Di_exp, 0.0
    # compute exp fit error in log domain
    mask = q > 0
    if mask.sum() < 3:
        return best_qi, best_Di, best_b
    q_ = q[mask]
    dts = np.array([dates[i] for i, m in enumerate(mask) if m])
    t0 = dts[0]
    t_years = np.array([(_months_between(t0, d) / 12.0) for d in dts], dtype=float)
    lnq = np.log(q_)
    base_err = float(((lnq - (math.log(qi_exp) - Di_exp * t_years)) ** 2).mean())
    best_err = base_err

    if not prefer_hyperbolic:
        return best_qi, best_Di, best_b

    for b in np.linspace(0.1, 1.0, 10):
        # try small grids around Di and qi
        for Di in Di_exp * np.array([0.5, 0.75, 1.0, 1.25, 1.5]):
            f = arps_rate(qi_exp, max(1e-6, Di), b, t_years)
            err = float(((np.log(q_) - np.log(np.maximum(f, 1e-9))) ** 2).mean())
            if err < best_err:
                best_qi, best_Di, best_b, best_err = qi_exp, float(Di), float(b), err
        for qi in qi_exp * np.array([0.5, 0.75, 1.0, 1.25, 1.5]):
            f = arps_rate(max(1e-6, qi), Di_exp, b, t_years)
            err = float(((np.log(q_) - np.log(np.maximum(f, 1e-9))) ** 2).mean())
            if err < best_err:
                best_qi, best_Di, best_b, best_err = float(qi), Di_exp, float(b), err

    return best_qi, best_Di, best_b


# ---------- Scenario engine ----------
def simulate_scenarios(
    start_date: date,
    months: int,
    oil_fit: Tuple[float, float, float],
    gas_fit: Tuple[float, float, float],
    base_wc: float,
    inj_rules: Dict[str, dict],
    new_wells: List[Dict[str, str]],
    wor_model: Dict[str, float] | None,
    gor_model: Dict[str, float] | None,
) -> pd.DataFrame:
    """Monthly profile with columns: oil_rate, gas_rate, water_rate, cum_oil, cum_gas, cum_water."""
    qi_o, Di_o, b_o = oil_fit
    qi_g, Di_g, b_g = gas_fit

    idx = pd.date_range(start=start_date, periods=months, freq="MS")
    t_years = np.arange(months, dtype=float) / 12.0

    def D_eff(D, inj: dict, i: int) -> float:
        if not inj:
            return D
        i0 = max(0, _months_between(start_date, inj.get("start") or start_date))
        support = float(inj.get("support", 0.0))
        return D * (max(0.1, 1.0 - support) if i >= i0 else 1.0)

    oil = np.zeros(months)
    gas = np.zeros(months)

    # base streams
    for i in range(months):
        Do = D_eff(Di_o, inj_rules.get("oil") or inj_rules.get("gas"), i)
        Dg = D_eff(Di_g, inj_rules.get("gas"), i)
        oil[i] = arps_rate(qi_o, Do, b_o, np.array([t_years[i]])).item()
        gas[i] = arps_rate(qi_g, Dg, b_g, np.array([t_years[i]])).item()

    # new wells (clone oil decline with qi_factor)
    if new_wells:
        for w in new_wells:
            sdt = _to_date(w.get("start"))
            if not sdt:
                continue
            i0 = max(0, _months_between(start_date, sdt))
            qi_fac = float(w.get("qi_factor", 1.0))
            for i in range(i0, months):
                Do = D_eff(Di_o, inj_rules.get("oil") or inj_rules.get("gas"), i)
                t = (i - i0) / 12.0
                oil[i] += arps_rate(qi_o * qi_fac, Do, b_o, np.array([t])).item()

    # WOR model overrides watercut if provided
    if wor_model:
        # WOR = a + b * Np   => wc = WOR/(1+WOR)
        factor = 30.437  # days/month
        cum_oil = np.cumsum(oil * factor)
        WOR = wor_model["a"] + wor_model["b"] * cum_oil
        wc = np.clip(WOR / (1.0 + np.maximum(WOR, 1e-9)), 0.0, 0.98)
    else:
        wc = np.clip(base_wc + np.linspace(0, 0.2, months), 0.0, 0.98)
        if inj_rules.get("water"):
            i0 = max(0, _months_between(start_date, inj_rules["water"].get("start") or start_date))
            for i in range(i0, months):
                wc[i] = wc[i0] + (wc[i] - wc[i0]) * (1.0 - float(inj_rules["water"].get("support", 0.2)))

    water = oil * wc
    oil_eff = np.maximum(0.0, oil - water)

    # GOR model can override gas
    if gor_model:
        GOR = gor_model["a"] + gor_model["b"] * np.arange(months)  # simple time trend
        gas = np.maximum(0.0, oil_eff * np.maximum(GOR, 0.0))

    # Cum (assume daily rates → monthly volume)
    factor = 30.437
    cum_oil = np.cumsum(oil_eff * factor)
    cum_gas = np.cumsum(gas * factor)
    cum_water = np.cumsum(water * factor)

    return pd.DataFrame(
        {
            "date": idx,
            "oil_rate": oil_eff,
            "gas_rate": gas,
            "water_rate": water,
            "cum_oil": cum_oil,
            "cum_gas": cum_gas,
            "cum_water": cum_water,
        }
    )


# ---------- UI / Controller ----------
def run(stage: str):
    st.header("Subsurface — Data-Driven Forecasts (with OOIP/OGIP, WOR & GOR)")
    deliverable = DELIV_BY_STAGE.get(stage, "Reservoir Profiles")
    _ensure_deliverable(stage, deliverable)  # :contentReference[oaicite:5]{index=5}

    st.markdown("Upload history (CSV with `date, oil_rate, gas_rate, water_rate, pressure` optional).")
    f = st.file_uploader("CSV file", type=["csv"])
        # ----- Composition (required for Engineering) -----
    st.markdown("### Fluid Composition (mole fraction) – required for Engineering")

    c_top = st.columns(3)
    with c_top[0]:
        T_res_C = st.number_input("Reservoir Temperature (°C)", 0.0, 300.0, 95.0)
    with c_top[1]:
        P_res_bar = st.number_input("Reservoir Pressure (bar)", 0.0, 1200.0, 240.0)
    with c_top[2]:
        sal_ppm = st.number_input("Water Salinity (ppm)", 0.0, 300000.0, 35000.0)

    st.caption("Enter mole fractions; they will be normalized to sum to 1.0 if needed.")

    col_g, col_o = st.columns(2)
    with col_g:
        st.subheader("Reservoir Gas zᵢ")
        gas_df = st.data_editor(
            pd.DataFrame(DEFAULT_GAS),
            num_rows="dynamic",
            key="comp_gas_df",
            use_container_width=True,
        )
        gas_df = _normalize_z(gas_df)

        if not _z_sum_ok(gas_df):
            st.error("Gas composition does not sum to 1.0 (after normalization). Please check.")

    with col_o:
        st.subheader("Stock-Tank Oil (pseudo) zᵢ")
        oil_df = st.data_editor(
            pd.DataFrame(DEFAULT_OIL_PSEUDO),
            num_rows="dynamic",
            key="comp_oil_df",
            use_container_width=True,
        )
        oil_df = _normalize_z(oil_df)

        if not _z_sum_ok(oil_df):
            st.error("Oil pseudo composition does not sum to 1.0 (after normalization). Please check.")

    st.subheader("Injected Gas (optional)")
    inj_df = st.data_editor(
        pd.DataFrame(DEFAULT_INJ_GAS),
        num_rows="dynamic",
        key="comp_inj_df",
        use_container_width=True,
    )
    inj_df = _normalize_z(inj_df)

    # Forecast horizon & fitting options
    cA, cB, cC, cD = st.columns(4)
    with cA:
        years_forward = st.number_input("Forecast years", 1, 50, 20)
    with cB:
        base_wc = st.slider("Base watercut fraction", 0.0, 0.95, 0.1, 0.01)
    with cC:
        prefer_hyp = st.checkbox("Try hyperbolic (b∈[0.1..1])", True)
    with cD:
        smooth = st.checkbox("Smooth history (3-point)", True)

    # Reserves / limits
    st.markdown("#### OOIP / OGIP & Recovery")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        ooip = st.number_input("OOIP (MMstb)", 0.0, 1e6, 500.0)
    with r2:
        rfo = st.slider("RF oil (%)", 0.0, 100.0, 35.0, 0.5)
    with r3:
        ogip = st.number_input("OGIP (Bscf)", 0.0, 1e7, 800.0)
    with r4:
        rfg = st.slider("RF gas (%)", 0.0, 100.0, 80.0, 0.5)

    # Scenario controls
    st.markdown("#### Development Scenarios")
    wells_df = st.data_editor(
        pd.DataFrame([{"start": "", "qi_factor": 1.0}]),
        num_rows="dynamic",
        key="sub_new_wells",
    )
    s1, s2 = st.columns(2)
    with s1:
        gas_inj = st.checkbox("Gas injection", False)
        g_start = st.text_input("Gas inj start (YYYY-MM)", "")
        g_support = st.slider("Gas support", 0.0, 0.9, 0.3, 0.05)
    with s2:
        water_inj = st.checkbox("Water injection", False)
        w_start = st.text_input("Water inj start (YYYY-MM)", "")
        w_support = st.slider("Water support (slows WOR rise)", 0.0, 0.9, 0.2, 0.05)

    # Advanced fits
    st.markdown("#### Advanced Fits (optional)")
    a1, a2 = st.columns(2)
    with a1:
        use_wor = st.checkbox("Use WOR vs cumulative oil", True)
    with a2:
        use_gor = st.checkbox("Use GOR trend (time)", False)

    # Load/prepare history
    if f:
        try:
            hist = pd.read_csv(io.BytesIO(f.read()))
            hist = _ensure_datetime_index(hist)
            if smooth:
                for c in ("oil_rate", "gas_rate", "water_rate"):
                    if c in hist.columns:
                        hist[c] = hist[c].rolling(3, min_periods=1, center=True).mean()
            st.success(f"Loaded {len(hist)} history rows.")
            st.dataframe(hist.tail(12))
        except Exception as ex:
            st.error(f"CSV parse error: {ex}")
            return
    else:
        # synthetic minimal history if none provided
        today = date.today().replace(day=1)
        idx = pd.date_range(end=today, periods=12, freq="MS")
        hist = pd.DataFrame(
            {
                "oil_rate": np.linspace(12000, 9500, len(idx)),
                "gas_rate": np.linspace(15_000_000, 12_000_000, len(idx)),
                "water_rate": np.linspace(1500, 2500, len(idx)),
            },
            index=idx,
        )
        st.info("No CSV provided — using synthetic 12-month history for demo.")

    # Fit Arps
    dts = [d.date() for d in hist.index.to_pydatetime()]
    oil_fit = fit_arps(dts, hist.get("oil_rate", pd.Series(dtype=float)).fillna(0).to_numpy(), prefer_hyperbolic=prefer_hyp)
    gas_fit = fit_arps(dts, hist.get("gas_rate", pd.Series(dtype=float)).fillna(0).to_numpy(), prefer_hyperbolic=prefer_hyp)

    st.markdown("##### Fitted parameters")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Oil qi", f"{oil_fit[0]:,.0f}")
    with c2: st.metric("Oil Di (1/yr)", f"{oil_fit[1]:.3f}")
    with c3: st.metric("Oil b", f"{oil_fit[2]:.2f}")
    c4, c5, c6 = st.columns(3)
    with c4: st.metric("Gas qi", f"{gas_fit[0]:,.0f}")
    with c5: st.metric("Gas Di (1/yr)", f"{gas_fit[1]:.3f}")
    with c6: st.metric("Gas b", f"{gas_fit[2]:.2f}")

    # Build models
    inj_rules = {}
    if gas_inj:
        inj_rules["gas"] = {"start": _to_date(g_start) or date.today(), "support": g_support}
        inj_rules["oil"] = {"start": _to_date(g_start) or date.today(), "support": g_support * 0.8}
    if water_inj:
        inj_rules["water"] = {"start": _to_date(w_start) or date.today(), "support": w_support}

    new_wells = []
    if isinstance(wells_df, pd.DataFrame) and not wells_df.empty:
        for _, row in wells_df.iterrows():
            s = str(row.get("start", "")).strip()
            qf = float(row.get("qi_factor", 1.0))
            if s:
                new_wells.append({"start": s, "qi_factor": qf})

    # WOR fit (from history)
    wor_model = None
    if use_wor and "oil_rate" in hist and "water_rate" in hist:
        oil = hist["oil_rate"].clip(lower=1e-9)
        WOR = (hist["water_rate"] / oil).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        factor = 30.437
        Np = oil.mul(factor).cumsum()
        try:
            A = np.vstack([np.ones(len(Np)), Np.to_numpy()]).T
            x, *_ = np.linalg.lstsq(A, WOR.to_numpy(), rcond=None)
            wor_model = {"a": float(x[0]), "b": float(x[1])}
        except Exception:
            wor_model = None

    # GOR trend (linear vs time)
    gor_model = None
    if use_gor and "oil_rate" in hist and "gas_rate" in hist:
        oil = hist["oil_rate"].clip(lower=1e-9)
        GOR = (hist["gas_rate"] / oil).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        t = np.arange(len(GOR))
        try:
            A = np.vstack([np.ones_like(t), t]).T
            x, *_ = np.linalg.lstsq(A, GOR.to_numpy(), rcond=None)
            gor_model = {"a": float(x[0]), "b": float(x[1])}
        except Exception:
            gor_model = None

    # Simulate
    months = int(years_forward * 12)
    start_date = (hist.index[-1] + pd.offsets.MonthBegin(1)).date()
    prof = simulate_scenarios(start_date, months, oil_fit, gas_fit, base_wc, inj_rules, new_wells, wor_model, gor_model)

    st.markdown("#### Forecast Preview")
    st.line_chart(prof.set_index("date")[["oil_rate", "gas_rate", "water_rate"]])

    # Depletion metrics
    # A) rate-based: oil_rate < 5% of initial simulated oil
    thr_rate = 0.05 * float(prof["oil_rate"].iloc[0])
    dep_idx_r = np.argmax(prof["oil_rate"].to_numpy() < thr_rate)
    dep_date_r = prof["date"].iloc[dep_idx_r] if dep_idx_r > 0 else prof["date"].iloc[-1]

    # B) reserves-based: cum_oil >= OOIP * RF ; cum_gas >= OGIP * RF
    oil_limit = ooip * 1e6 * (rfo / 100.0)   # MMstb → stb
    gas_limit = ogip * 1e9 * (rfg / 100.0)   # Bscf → scf
    dep_idx_o = np.argmax(prof["cum_oil"].to_numpy() >= oil_limit)
    dep_idx_g = np.argmax(prof["cum_gas"].to_numpy() >= gas_limit)
    dep_date_o = prof["date"].iloc[dep_idx_o] if dep_idx_o > 0 else None
    dep_date_g = prof["date"].iloc[dep_idx_g] if dep_idx_g > 0 else None

    cD1, cD2, cD3 = st.columns(3)
    with cD1: st.metric("Depletion (rate<5%)", str(dep_date_r))
    with cD2: st.metric("Oil reaches RF", str(dep_date_o) if dep_date_o else "—")
    with cD3: st.metric("Gas reaches RF", str(dep_date_g) if dep_date_g else "—")

    # Exports
    st.markdown("#### Export")
    # CSV
    csv_bytes = prof.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name="reservoir_profiles.csv", mime="text/csv")
    # XLSX
    try:
        import io as _io
        from pandas import ExcelWriter
        xbuf = _io.BytesIO()
        with pd.ExcelWriter(xbuf, engine="xlsxwriter") as writer:
            prof.to_excel(writer, index=False, sheet_name="Forecast")
            info = pd.DataFrame({
                "key": ["OOIP (stb)", "RF oil (%)", "OGIP (scf)", "RF gas (%)",
                        "Rate threshold", "Depl (rate<5%)", "Depl oil @RF", "Depl gas @RF"],
                "value": [oil_limit, rfo, gas_limit, rfg, thr_rate, str(dep_date_r), str(dep_date_o), str(dep_date_g)]
            })
            info.to_excel(writer, index=False, sheet_name="Summary")
        st.download_button("Download XLSX", data=xbuf.getvalue(), file_name="reservoir_profiles.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as ex:
        st.caption(f"XLSX export unavailable: {ex}")

    # PDF (compact one-pager)
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Reservoir Forecast Report", ln=1)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, f"Stage: {stage}\n"
                              f"History rows: {len(hist)}\n"
                              f"OOIP: {ooip:.2f} MMstb  RF: {rfo:.1f}%\n"
                              f"OGIP: {ogip:.2f} Bscf  RF: {rfg:.1f}%\n"
                              f"Depletion (rate<5%): {dep_date_r}\n"
                              f"Oil reaches RF: {dep_date_o}\n"
                              f"Gas reaches RF: {dep_date_g}")
        out = pdf.output(dest="S").encode("latin1", "ignore")
        st.download_button("Download PDF", data=out, file_name="reservoir_report.pdf", mime="application/pdf")
    except Exception as ex:
        st.caption(f"PDF export unavailable: {ex}")

    # Approve & save as artifact (enables cascade)
    if st.button("Generate & Approve Reservoir Profiles"):
        _mark_deliverable(stage, deliverable, "Done")
        _set_artifact_status(ARTIFACT, "Approved")

        project_id = st.session_state.get("current_project_id", "P-DEMO")
        phase_id   = st.session_state.get("current_phase_id", f"PH-{stage}")

        payload = {
            "history_points": int(len(hist)),
            "fit_params": {
                "oil": {"qi": float(oil_fit[0]), "Di": float(oil_fit[1]), "b": float(oil_fit[2])},
                "gas": {"qi": float(gas_fit[0]), "Di": float(gas_fit[1]), "b": float(gas_fit[2])},
            },
            "reserves": {
                "OOIP_stb": float(ooip) * 1e6,
                "RF_oil_pct": float(rfo),
                "OGIP_scf": float(ogip) * 1e9,
                "RF_gas_pct": float(rfg),
            },
            "scenarios": {
                "new_wells": new_wells,
                "injection": {"gas": inj_rules.get("gas"), "water": inj_rules.get("water")},
                "base_watercut": float(base_wc),
                "models": {"WOR": wor_model, "GOR": gor_model},
            },
            "conditions": {
                "reservoir_T_C": float(T_res_C),
                "reservoir_P_bar": float(P_res_bar),
                "water_salinity_ppm": float(sal_ppm),
            },
            "composition": {
                "gas": [
                    {"component": str(r["component"]), "z": float(r["z"])}
                    for _, r in gas_df.iterrows()
                ],
                "oil": [
                    {"component": str(r["component"]), "z": float(r["z"])}
                    for _, r in oil_df.iterrows()
                ],
                "inj_gas": [
                    {"component": str(r["component"]), "z": float(r["z"])}
                    for _, r in inj_df.iterrows()
                ],
            },
            "dates": [d.strftime("%Y-%m-%d") for d in prof["date"]],
            "oil_rate": prof["oil_rate"].round(6).tolist(),
            "gas_rate": prof["gas_rate"].round(6).tolist(),
            "water_rate": prof["water_rate"].round(6).tolist(),
            "cum_oil": prof["cum_oil"].round(3).tolist(),
            "cum_gas": prof["cum_gas"].round(3).tolist(),
            "cum_water": prof["cum_water"].round(3).tolist(),
            "depletion": {
                "rate_threshold": float(thr_rate),
                "by_rate": str(dep_date_r),
                "oil_at_RF": (str(dep_date_o) if dep_date_o else None),
                "gas_at_RF": (str(dep_date_g) if dep_date_g else None),
            },
        }

        # Persist as Approved → emits artifact.approved for cascade
        save_artifact(project_id, phase_id, "Subsurface", ARTIFACT, payload, status="Approved")
        st.success("Reservoir Profiles generated, approved, and saved for downstream modules.")
    if st.button("Proceed to Engineering ▶"):
        st.session_state["force_open_module"] = "Engineering"
        st.session_state["open_module"] = "Engineering"
        st.session_state["view"] = "Modules"
        st.rerun()

