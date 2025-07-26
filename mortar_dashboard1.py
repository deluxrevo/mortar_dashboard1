import streamlit as st
from datetime import date

st.set_page_config(page_title="Spray Mortar Dashboard", layout="wide")

# Sidebar Navigation
st.sidebar.title("🚧 Spray Mortar Rollout")
phase = st.sidebar.radio("Select Phase", [
    "📊 Overview", "🧪 Recipe Mixer", "🔁 Batch Tracker", 
    "📦 Packaging Setup", "🏗️ Site Trials", "💼 Sales Prep"
])

# Overview Tab
if phase == "📊 Overview":
    st.title("🧱 Spray Mortar Finalization")
    st.metric("🎯 Target Launch", "3 Weeks")
    st.metric("📍 Current Status", "Trial Batch In Progress")
    st.progress(2/6)
    st.text("Use sidebar to navigate production phases.")

# Recipe Mixer Tab
elif phase == "🧪 Recipe Mixer":
    st.title("🧪 Mortar Recipe Mixer")

    cement = st.number_input("Cement (kg/tonne)", value=250)
    lime = st.number_input("Hydrated Lime (kg/tonne)", value=50)
    hpmc = st.number_input("HPMC (kg/tonne)", value=15)
    plasticizer = st.number_input("Plasticizer (kg/tonne)", value=0.5)
    kaolin_percent = st.slider("Kaolin content in sand (%)", 0, 20, value=5)

    adjusted_water = 210 + kaolin_percent * 2.5
    st.info(f"💧 Estimated Water Demand: {adjusted_water} kg/tonne")

# Batch Tracker Tab
elif phase == "🔁 Batch Tracker":
    st.title("🔁 Pilot Batch Tracker")

    batch_id = st.text_input("Batch Name")
    coverage = st.number_input("Coverage per 25kg (m²)", value=5.5)
    setting_time = st.text_input("Setting Time (minutes)", value="90")
    st.file_uploader("📷 Upload spray test photo")
    st.text_area("👷 Contractor Feedback")

# Packaging Setup Tab
elif phase == "📦 Packaging Setup":
    st.title("📦 Packaging Details")

    product_name = st.text_input("Product Name", value="ES Spray Mortar")
    bag_weight = st.selectbox("Bag Size", ["25 kg", "30 kg"])
    label_text = st.text_area("Label Content", value="Fast sprayable mortar with smooth finish")
    st.checkbox("💧 Moisture-resistant bags")
    st.date_input("Label Batch Date", value=date.today())
    st.text("You can export label design separately with PDF tools.")

# Site Trials Tab
elif phase == "🏗️ Site Trials":
    st.title("🏗️ Real-Site Trials")

    site_name = st.text_input("Site Name")
    trial_date = st.date_input("Trial Date", value=date.today())
    st.file_uploader("📸 Upload trial wall photos")
    feedback = st.text_area("🧱 Observations / Finish Details")

# Sales Prep Tab
elif phase == "💼 Sales Prep":
    st.title("💼 Commercial Launch Prep")

    price = st.number_input("Retail Price per Sack (MAD)", value=38)
    bulk_discount = st.checkbox("Apply Bulk Pricing")
    st.text_area("📣 Sales Pitch", value="High-speed spray plaster with exceptional finish and reduced labor.")
    st.file_uploader("🎬 Upload Demo Video or Flyer")

# Footer
st.markdown("---")
st.caption("Created for Omar • Built with Streamlit • Morocco 🇲🇦")
