# streamlit_app.py
import io
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

# --- Constants ---
MORTAR_FLAG_THRESHOLDS = {
    "unsuitable": {"mbv": 4.0, "se": 70, "fines": 15},
    "safe": {"mbv": 2.5, "se": 75, "fines": 10},
}
DEFAULT_PSD_TEXT = (
    "12.2: 100\n10: 90\n8: 80\n6.3: 64\n5.2: 61\n4: 60\n3.2: 52\n2.5: 45\n2: 42\n"
    "1.25: 30\n1: 30\n0.8: 27\n0.5: 24\n0.4: 22\n0.355: 21\n0.315: 17\n0.250: 17\n"
    "0.180: 16\n0.160: 15\n0.125: 14\n0.100: 14\n0.090: 14\n0.063: 13.7"
)

# --- Helper Functions ---
def parse_text_sieve(text: str) -> pd.DataFrame:
    """Parses multiline text into a Particle Size Distribution (PSD) DataFrame."""
    rows = []
    for line in text.strip().split("\n"):
        if ":" not in line.strip():
            continue
        try:
            size, pct = line.split(":")
            rows.append((float(size.strip()), float(pct.strip())))
        except (ValueError, IndexError):
            # Silently ignore malformed lines
            pass
    return pd.DataFrame(rows, columns=["Sieve_mm", "Passing_pct"])

def parse_csv(file: UploadedFile) -> pd.DataFrame:
    """Parses a CSV file into a standard PSD DataFrame."""
    df = pd.read_csv(file)
    cols = {c.lower(): c for c in df.columns}
    sieve_col = cols.get("sieve_mm") or cols.get("sieve") or cols.get("size_mm") or df.columns[0]
    pass_col = cols.get("passing_pct") or cols.get("passing") or cols.get("%passing") or df.columns[1]
    
    out = df[[sieve_col, pass_col]].copy()
    out.columns = ["Sieve_mm", "Passing_pct"]
    return out.dropna().astype({"Sieve_mm": "float", "Passing_pct": "float"})

def interpolate_passing_at(df: pd.DataFrame, cutoff_mm: float) -> float:
    """Interpolates the passing percentage at a specific sieve size."""
    if df.empty:
        return float("nan")
    
    df_sorted = df.sort_values("Sieve_mm", ascending=False).reset_index()
    sizes = df_sorted["Sieve_mm"].values
    passing = df_sorted["Passing_pct"].values

    if cutoff_mm > sizes[0]:
        return passing[0]
    if cutoff_mm < sizes[-1]:
        return passing[-1]

    for i in range(len(sizes) - 1):
        s_hi, s_lo = sizes[i], sizes[i+1]
        p_hi, p_lo = passing[i], passing[i+1]
        
        if abs(s_hi - cutoff_mm) < 1e-9:
            return p_hi
        
        if s_hi >= cutoff_mm >= s_lo:
            if abs(s_hi - s_lo) < 1e-12:
                return (p_hi + p_lo) / 2.0
            
            # Linear interpolation
            t = (cutoff_mm - s_lo) / (s_hi - s_lo)
            return p_lo + t * (p_hi - p_lo)
            
    return float("nan")

def get_mortar_compatibility(mbv: float, se: int, fines: float) -> str:
    """Determines mortar compatibility based on QC parameters."""
    # 1. First, check for the "premium" case.
    safe = MORTAR_FLAG_THRESHOLDS["safe"]
    if mbv <= safe["mbv"] and se >= safe["se"] and fines <= safe["fines"]:
        return "✅ Safe for all mortar types"

    # 2. If not premium, then check if it's "unsuitable".
    unsuitable = MORTAR_FLAG_THRESHOLDS["unsuitable"]
    if mbv > unsuitable["mbv"] or se < unsuitable["se"] or fines > unsuitable["fines"]:
        return "❌ Not suitable for tile/self-leveling"
    
    # 3. If it's neither premium nor unsuitable, it's intermediate.
    return "⚠️ Use only in plaster or screed"


def generate_qc_report(fines_cutoff, fines_percent, mbv, se, compatibility, df_psd) -> str:
    """Generates a markdown summary of the QC results."""
    return f"""
# Sand QC Summary

- Fines cutoff: < {fines_cutoff} mm
- Fines percent: {fines_percent:.1f}%
- MBV: {mbv:.1f} mg/g
- Sand Equivalent (NF EN 933-8): {se}
- Mortar compatibility: {compatibility}

## PSD Table (Cumulative Passing)

{df_psd.to_markdown(index=False)}
"""

def mass_balance_after_reject(feed_fines_pct, reject_rate_pct, reject_fines_grade_pct) -> float:
    """Calculates the fines percentage in the product stream after classification."""
    fF = feed_fines_pct / 100.0
    R = max(0.0, min(1.0, reject_rate_pct / 100.0))
    fR = max(0.0, min(1.0, reject_fines_grade_pct / 100.0))
    
    fines_feed_mass = 1.0 * fF
    reject_mass = 1.0 * R
    fines_reject_mass = reject_mass * fR
    
    product_mass = 1.0 - reject_mass
    product_fines_mass = max(0.0, fines_feed_mass - fines_reject_mass)
    
    return 100.0 * product_fines_mass / max(1e-9, product_mass)

def setup_sidebar():
    """Configures and returns all sidebar inputs."""
    st.sidebar.header("🧪 Input lab data")
    mbv = st.sidebar.number_input("MBV (mg/g)", 0.0, 20.0, 6.5, 0.1)
    se = st.sidebar.number_input("Sand Equivalent (SE)", 0, 100, 65, 1)
    fines_cutoff = st.sidebar.selectbox("Fines cutoff (mm)", [0.075, 0.063, 0.05, 0.1], 1)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📄 Upload PSD CSV (optional)")
    csv_file = st.sidebar.file_uploader("CSV with columns: Sieve_mm, Passing_pct", type=["csv"])

    st.sidebar.subheader("📝 Or paste PSD text (mm : % passing)")
    text_area = st.sidebar.text_area("Paste PSD lines", DEFAULT_PSD_TEXT, height=200)
    
    return mbv, se, fines_cutoff, csv_file, text_area

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="Sand QC Dashboard", page_icon="🧱", layout="wide")

    # --- Initialize Session State ---
    if "qc_history" not in st.session_state:
        st.session_state.qc_history = pd.DataFrame(columns=[
            "timestamp", "fines_cutoff_mm", "fines_pct", "MBV_mg_g", "SE", "compatibility"
        ])

    # --- Sidebar and Data Loading ---
    mbv, se, fines_cutoff, csv_file, text_area = setup_sidebar()

    df_psd = parse_csv(csv_file) if csv_file else parse_text_sieve(text_area)
    
    if df_psd.empty or df_psd.shape[1] < 2:
        st.error("No valid PSD data found. Please upload a CSV or paste text data in 'mm : %' format.")
        st.stop()
    
    df_psd = df_psd.sort_values("Sieve_mm", ascending=False)
    fines_percent = interpolate_passing_at(df_psd, fines_cutoff)
    compatibility = get_mortar_compatibility(mbv, se, fines_percent)

    # --- Main Page Layout ---
    col1, col2, col3 = st.columns([1.2, 1, 1])

    with col1:
        st.title("🧱 Sand QC Dashboard")
        st.caption("SE, MBV, and PSD-driven compatibility analysis.")
        
        m1, m2, m3 = st.columns(3)
        m1.metric(f"Fines < {fines_cutoff} mm", f"{fines_percent:.1f}%")
        m2.metric("MBV", f"{mbv:.1f} mg/g")
        m3.metric("Sand Equivalent", f"{se}")

        st.subheader("🧪 Mortar Compatibility")
        if "✅" in compatibility:
            st.success(compatibility)
        elif "⚠️" in compatibility:
            st.warning(compatibility)
        else:
            st.error(compatibility)
        
        st.subheader("📊 PSD Table")
        st.dataframe(df_psd, use_container_width=True)

    with col2:
        st.subheader("📦 Silo Split Recommendation")
        if fines_percent > 20:
            st.warning("**High fines:** Use separate filler silo and dose by QC rules.")
        elif fines_percent >= 10:
            st.info("**Moderate fines:** Monitor MBV & SE; controlled dosing recommended.")
        else:
            st.success("**Low fines:** Likely safe for direct feed; validate for sensitive mortars.")

        st.markdown("---")
        st.subheader("🛠️ Classifier Tuning (Mass Balance)")
        feed_fines_pct = st.number_input("Feed fines% (< cutoff)", 0.0, 100.0, float(fines_percent), 0.1)
        reject_rate_pct = st.number_input("Reject rate% (mass)", 0.0, 90.0, 15.0, 0.5)
        reject_fines_grade_pct = st.number_input("Reject fines grade% (< cutoff)", 0.0, 100.0, 85.0, 1.0)
        
        product_fines_pct = mass_balance_after_reject(feed_fines_pct, reject_rate_pct, reject_fines_grade_pct)
        st.metric("Estimated Product Fines% (< cutoff)", f"{product_fines_pct:.1f}%")
        st.caption("Preview air-cut impact. Tune reject rate to hit target product fines.")

    with col3:
        st.subheader("🧾 History & Export")
        if st.button("Add Current Entry to History"):
            new_entry = pd.DataFrame([{
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "fines_cutoff_mm": fines_cutoff,
                "fines_pct": round(fines_percent, 2),
                "MBV_mg_g": round(mbv, 2),
                "SE": int(se),
                "compatibility": compatibility
            }])
            st.session_state.qc_history = pd.concat([st.session_state.qc_history, new_entry], ignore_index=True)
            st.success("Entry added to history.")

        if not st.session_state.qc_history.empty:
            st.dataframe(st.session_state.qc_history, use_container_width=True, height=260)
            csv_buf = st.session_state.qc_history.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download History CSV", csv_buf, "qc_history.csv", "text/csv")

        st.markdown("---")
        st.subheader("📝 Export QC Report (Markdown)")
        report_md = generate_qc_report(fines_cutoff, fines_percent, mbv, se, compatibility, df_psd)
        st.download_button("⬇️ Download QC Report", report_md, "qc_report.md", "text/markdown")

    with st.expander("📘 Quick Guidance"):
        st.markdown(
            "- **Cutoff Choice:** Use 0.063–0.075 mm for fines relevant to mortars.\n"
            "- **Targets:** **SE ≥ 75**, **MBV ≤ 2.5 mg/g**, **fines ≤ 10%** for sensitive mortars.\n"
            "- **Validation:** Always retest SE/MBV after classification before scaling."
        )

if __name__ == "__main__":
    main()
