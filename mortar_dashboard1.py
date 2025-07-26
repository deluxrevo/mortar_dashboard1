import streamlit as st
from datetime import date

st.set_page_config(page_title="ES 47 Spray Mortar Dashboard", layout="wide")

# Sidebar Navigation
st.sidebar.title("🧱 Omar's Spray Mortar Rollout")
phase = st.sidebar.radio("Select Phase", [
    "📊 Overview", "🧪 Recipe Snapshot", "🔁 Batch Tracker", 
    "📦 Packaging & Labeling", "🏗️ Site Trials", "💼 Sales Prep"
])

# Overview Tab
if phase == "📊 Overview":
    st.title("🧱 ES 47 Mortar Finalization")
    st.metric("🎯 Target Launch", "3 Weeks")
    st.metric("📍 Current Status", "Recipe Locked")
    st.progress(2/6)
    st.caption("Track your production phases and test results here.")

# Recipe Snapshot Tab
elif phase == "🧪 Recipe Snapshot":
    st.title("🧪 Official Mix - Spray Mortar (1 tonne)")
    st.write("""
    - **🟠 Sable calibré ES 47:** 700 kg
    - **⚫ Ciment Portland 42.5:** 250 kg
    - **⚪ Chaux aérienne CL 90:** 30 kg
    - **🟡 Kaolin naturel:** 20 kg
    - **🟣 Hydrofuge Sika® Poudre:** 5 kg
    """)
    kaolin_slider = st.slider("Kaolin (%) in ES Sand", 0, 15, value=5)
    water_demand = 180 + kaolin_slider * 2.5
    st.success(f"💧 Est. Water Demand: {water_demand} kg/tonne")
    st.caption("Adjust water if kaolin-rich sand impacts workability.")

# Batch Tracker Tab
elif phase == "🔁 Batch Tracker":
    st.title("🔁 Test Batch Log")
    batch_name = st.text_input("Batch ID")
    coverage = st.number_input("Coverage per 25kg (m²)", value=6.0)
    set_time = st.text_input("Setting Time (min)", value="90")
    notes = st.text_area("Operator Comments")
    st.file_uploader("📷 Upload wall test photo")

# Packaging & Labeling Tab
elif phase == "📦 Packaging & Labeling":
    st.title("📦 Sack & Label Prep")
    product_name = st.text_input("Product Name", value="ES 47 Spray Mortar")
    label_text = st.text_area("Label Text", value="Prêt à projeter • Application rapide • Finition lisse")
    sack_weight = st.selectbox("Bag Size", ["25 kg", "30 kg"])
    batch_date = st.date_input("Batch Date", date.today())
    st.checkbox("✅ Use moisture-resistant packaging")
    st.caption("Add graphic labels separately using external PDF tools.")

# Site Trials Tab
elif phase == "🏗️ Site Trials":
    st.title("🏗️ Real-Site Trial Log")
    site = st.text_input("Site Name")
    date_trial = st.date_input("Trial Date", value=date.today())
    wall_feedback = st.text_area("Finish Observations")
    st.file_uploader("📸 Upload façade photo")

# Sales Prep Tab
elif phase == "💼 Sales Prep":
    st.title("💼 Commercial Launch Prep")
    retail_price = st.number_input("Price per Sack (MAD)", value=38)
    bulk_option = st.checkbox("Offer Bulk Discount?")
    pitch = st.text_area("📣 Sales Message", value="Mortier projetable rapide, finition parfaite, réduction main-d'œuvre.")
    st.file_uploader("🎬 Upload demo or flyer")

# Footer
st.markdown("---")
st.caption("Built for Omar • ES 47 Spray Mortar • Streamlit Morocco 🇲🇦")
