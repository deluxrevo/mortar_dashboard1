# streamlit_app.py
import streamlit as st
import pandas as pd
import io
from datetime import datetime
import math

st.set_page_config(page_title="Sand QC Dashboard", page_icon="🧱", layout="wide")

# ------------------------------
# Helpers
# ------------------------------
def parse_text_sieve(text: str) -> pd.DataFrame:
    # Expect lines like: "12.5: 100"
    rows = []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        if ":" not in line:
            continue
        size, pct = line.split(":")
        try:
            rows.append((float(size.strip()), float(pct.strip())))
        except:
            pass
    df = pd.DataFrame(rows, columns=["Sieve_mm", "Passing_pct"]).sort_values("Sieve_mm", ascending=False)
    return df

def parse_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    # Expect columns named like "Sieve_mm", "Passing_pct" (case-insensitive fallback)
    cols = {c.lower(): c for c in df.columns}
    sieve_col = cols.get("sieve_mm") or cols.get("sieve") or cols.get("size_mm") or list(df.columns)[0]
    pass_col = cols.get("passing_pct") or cols.get("passing") or cols.get("%passing") or list(df.columns)[1]
    out = df[[sieve_col, pass_col]].copy()
    out.columns = ["Sieve_mm", "Passing_pct"]
    out = out.dropna().astype({"Sieve_mm":"float","Passing_pct":"float"}).sort_values("Sieve_mm", ascending=False)
    return out

def interpolate_passing_at(df: pd.DataFrame, cutoff_mm: float) -> float:
    # Assumes df sorted descending by Sieve_mm (largest to smallest)
    sizes = df["Sieve_mm"].values
    passing = df["Passing_pct"].values
    # Exact match
    for i, s in enumerate(sizes):
        if abs(s - cutoff_mm) < 1e-9:
            return passing[i]
    # Find bracket around cutoff
    # We want two points s_hi > cutoff > s_lo (descending order)
    for i in range(len(sizes)-1):
        s_hi, s_lo = sizes[i], sizes[i+1]
        p_hi, p_lo = passing[i], passing[i+1]
        if s_hi >= cutoff_mm >= s_lo:
            # Linear interpolation on log-size or linear? Use linear size for simplicity.
            if abs(s_hi - s_lo) < 1e-12:
                return (p_hi + p_lo)/2.0
            t = (cutoff_mm - s_lo) / (s_hi - s_lo)
            return p_lo + t * (p_hi - p_lo)
    # If cutoff below min sieve, return last passing; if above max, return first
    if cutoff_mm < sizes[-1]:
        return passing[-1]
    if cutoff_mm > sizes[0]:
        return passing[0]
    return float("nan")

def mortar_flag(mbv: float, se: int, fines: float):
    # Conservative logic (no blending)
    if mbv > 4.0 or se < 70 or fines > 15:
        return "❌ Not suitable for tile/self-leveling"
    elif mbv <= 2.5 and se >= 75 and fines <= 10:
        return "✅ Safe for all mortar types"
    else:
        return "⚠️ Use only in plaster or screed"

def qc_summary_markdown(fines_cutoff, fines_percent, mbv, se, compatibility, df_psd):
    buf = io.StringIO()
    buf.write("# Sand QC Summary\n\n")
    buf.write(f"- Fines cutoff: < {fines_cutoff} mm\n")
    buf.write(f"- Fines percent: {fines_percent:.1f}%\n")
    buf.write(f"- MBV: {mbv:.1f} mg/g\n")
    buf.write(f"- Sand Equivalent (NF EN 933-8): {se}\n")
    buf.write(f"- Mortar compatibility: {compatibility}\n\n")
    buf.write("## PSD Table (Cumulative Passing)\n\n")
    buf.write(df_psd.to_markdown(index=False))
    return buf.getvalue()

def mass_balance_after_reject(feed_fines_pct: float, reject_rate_pct: float, reject_fines_grade_pct: float):
    """
    Simple two-stream mass balance:
    - Feed fines% in total (by mass)
    - Reject rate% of total mass goes to reject
    - Reject stream fines grade% (how fine the reject is)
    Returns: product fines% (remaining stream)
    """
    F = 1.0
    fF = feed_fines_pct/100.0
    R = max(0.0, min(1.0, reject_rate_pct/100.0))
    fR = max(0.0, min(1.0, reject_fines_grade_pct/100.0))
    # Fines in product = total fines - fines removed in reject
    fines_feed_mass = F * fF
    reject_mass = F * R
    fines_reject_mass = reject_mass * fR
    product_mass = F - reject_mass
    product_fines_mass = max(0.0, fines_feed_mass - fines_reject_mass)
    product_fines_pct = 100.0 * product_fines_mass / max(1e-9, product_mass)
    return product_fines_pct

# ------------------------------
# Sidebar Inputs
# ------------------------------
st.sidebar.header("🧪 Input lab data")

mbv = st.sidebar.number_input("MBV (mg/g)", min_value=0.0, max_value=20.0, value=6.5, step=0.1)
se = st.sidebar.number_input("Sand Equivalent (SE)", min_value=0, max_value=100, value=65, step=1)
fines_cutoff = st.sidebar.selectbox("Fines cutoff (mm)", [0.075, 0.063, 0.05, 0.1], index=1)

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Upload PSD CSV (optional)")
csv_file = st.sidebar.file_uploader("CSV with columns: Sieve_mm, Passing_pct", type=["csv"])

st.sidebar.subheader("📝 Or paste PSD text (mm : % passing)")
default_text = "12.2: 100\n10: 90\n8: 80\n6.3: 64\n5.2: 61\n4: 60\n3.2: 52\n2.5: 45\n2: 42\n1.25: 30\n1: 30\n0.8: 27\n0.5: 24\n0.4: 22\n0.355: 21\n0.315: 17\n0.250: 17\n0.180: 16\n0.160: 15\n0.125: 14\n0.100: 14\n0.090: 14\n0.063: 13.7"
text_area = st.sidebar.text_area("Paste PSD lines", default_text, height=200)

# ------------------------------
# Data assembly
# ------------------------------
if csv_file:
    df_psd = parse_csv(csv_file)
else:
    df_psd = parse_text_sieve(text_area)

# Guard against empty
if df_psd.empty or df_psd.shape[1] < 2:
    st.error("No valid PSD data found. Please upload CSV or paste text data in 'mm : %' format.")
    st.stop()

# ------------------------------
# Main Layout
# ------------------------------
col1, col2, col3 = st.columns([1.2,1,1])

with col1:
    st.title("🧱 Sand QC Dashboard")
    st.caption("SE, MBV, PSD-driven compatibility — no blending path.")

    fines_percent = interpolate_passing_at(df_psd.sort_values("Sieve_mm", ascending=False), fines_cutoff)
    st.metric(f"Fines < {fines_cutoff} mm", f"{fines_percent:.1f}%")
    st.metric("MBV", f"{mbv:.1f} mg/g")
    st.metric("Sand Equivalent (NF EN 933-8)", f"{se}")

    compatibility = mortar_flag(mbv, se, fines_percent)
    st.subheader("🧪 Mortar compatibility")
    if compatibility.startswith("✅"):
        st.success(compatibility)
    elif compatibility.startswith("⚠️"):
        st.warning(compatibility)
    else:
        st.error(compatibility)

    st.subheader("📊 PSD table")
    st.dataframe(df_psd, use_container_width=True)

with col2:
    st.subheader("📦 Silo split recommendation")
    if fines_percent > 20:
        st.warning("**High fines:** Use separate filler silo and dose by QC rules.")
    elif fines_percent >= 10:
        st.info("**Moderate fines:** Monitor MBV & SE; controlled dosing recommended.")
    else:
        st.success("**Low fines:** Likely safe to feed directly for plaster; validate for tile/SLC.")

    st.markdown("---")
    st.subheader("🛠️ Classifier tuning (mass balance)")
    feed_fines_pct = st.number_input("Feed fines% (< cutoff)", min_value=0.0, max_value=100.0, value=float(fines_percent), step=0.1)
    reject_rate_pct = st.number_input("Reject rate% (mass)", min_value=0.0, max_value=90.0, value=15.0, step=0.5)
    reject_fines_grade_pct = st.number_input("Reject fines grade% (< cutoff)", min_value=0.0, max_value=100.0, value=85.0, step=1.0)

    product_fines_pct = mass_balance_after_reject(feed_fines_pct, reject_rate_pct, reject_fines_grade_pct)
    st.metric("Estimated product fines% (< cutoff)", f"{product_fines_pct:.1f}%")

    st.caption("Use this to preview air-cut impact. Tune reject rate and fines grade to hit target product fines%.")

with col3:
    st.subheader("🧾 History & export")
    if "qc_history" not in st.session_state:
        st.session_state.qc_history = []

    if st.button("Add current entry to history"):
        st.session_state.qc_history.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "fines_cutoff_mm": fines_cutoff,
            "fines_pct": round(fines_percent, 2),
            "MBV_mg_g": round(mbv, 2),
            "SE": int(se),
            "compatibility": compatibility
        })
        st.success("Entry added to history.")

    if st.session_state.qc_history:
        df_hist = pd.DataFrame(st.session_state.qc_history)
        st.dataframe(df_hist, use_container_width=True, height=260)

        # Export CSV
        csv_buf = df_hist.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download history CSV", data=csv_buf, file_name="qc_history.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("📝 Export QC report (Markdown)")
    report_md = qc_summary_markdown(fines_cutoff, fines_percent, mbv, se, compatibility, df_psd)
    st.download_button("⬇️ Download QC report", data=report_md, file_name="qc_report.md", mime="text/markdown")

# ------------------------------
# Tips
# ------------------------------
with st.expander("📘 Quick guidance"):
    st.markdown(
        "- **Cutoff choice:** Use 0.063–0.075 mm for fines relevant to mortars.\n"
        "- **Targets:** **SE ≥ 75**, **MBV ≤ 2.5 mg/g**, **fines ≤ 10%** for sensitive mortars.\n"
        "- **Validation:** Always retest SE/MBV after classification before scaling dosing."
    )
