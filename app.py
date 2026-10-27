import streamlit as st

st.set_page_config(
    page_title="GLP-1 Evidence Explorer",
    page_icon="💊",
    layout="wide"
)

st.title("GLP-1 Evidence Explorer")
st.subheader("AI-Assisted Clinical & Pharmacoeconomic Evaluation")

st.info("Research prototype for educational use only.")

st.header("1. Patient Information")

col1, col2 = st.columns(2)

with col1:
    hba1c = st.number_input(
        "Baseline HbA1c (%)",
        min_value=4.0,
        max_value=15.0,
        value=8.5
    )

with col2:
    insurance = st.selectbox(
        "Insurance Type",
        ["Commercial", "Medicare", "Medicaid", "Uninsured"]
    )

st.header("2. Select Medications")

medications = st.multiselect(
    "Choose GLP-1-based therapies to compare",
    [
        "Ozempic (semaglutide)",
        "Rybelsus (oral semaglutide)",
        "Victoza (liraglutide)",
        "Trulicity (dulaglutide)",
        "Mounjaro (tirzepatide)"
    ],
    default=[
        "Ozempic (semaglutide)",
        "Mounjaro (tirzepatide)"
    ]
)

st.header("3. Clinical & Economic Comparison")

if st.button("Compare Medications"):
    if medications:
        st.success("Comparison selected!")
        st.write("Selected medications:", ", ".join(medications))
        st.write("Baseline HbA1c:", hba1c)
        st.write("Insurance:", insurance)
        st.info(
            "Clinical evidence, cost estimates, and AI analysis "
            "will be connected in the next development stages."
        )
    else:
        st.warning("Please select at least one medication.")

st.divider()
st.caption(
    "Research prototype | Not intended for clinical decision-making"
)
