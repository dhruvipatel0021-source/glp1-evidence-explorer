import streamlit as st
import requests
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
    if not medications:
        st.warning("Please select at least one medication.")
    else:
        import requests

        drug_names = {
            "Ozempic (semaglutide)": "semaglutide",
            "Rybelsus (oral semaglutide)": "semaglutide",
            "Victoza (liraglutide)": "liraglutide",
            "Trulicity (dulaglutide)": "dulaglutide",
            "Mounjaro (tirzepatide)": "tirzepatide"
        }

        selected = [drug_names[m] for m in medications]

        drug_query = " OR ".join(
            f'"{drug}"[Title/Abstract]' for drug in selected
        )

        query = (
            f"({drug_query}) AND "
            '"Diabetes Mellitus, Type 2"[MeSH Terms] AND '
            '"randomized controlled trial"[Publication Type]'
        )

        with st.spinner("Searching PubMed..."):
            try:
                response = requests.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    params={
                        "db": "pubmed",
                        "term": query,
                        "retmax": 20,
                        "retmode": "json"
                    },
                    timeout=30
                )

                response.raise_for_status()
                pmids = response.json()["esearchresult"]["idlist"]

                st.success(f"Retrieved {len(pmids)} PubMed records!")

                for pmid in pmids:
                    st.markdown(
                        f"- [View study {pmid}]"
                        f"(https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
                    )

                st.info(
                    "AI extraction and clinical comparison "
                    "will be added next."
                )

            except requests.RequestException as e:
                st.error(f"PubMed search error: {e}")
st.divider()
st.caption(
    "Research prototype | Not intended for clinical decision-making"
)
