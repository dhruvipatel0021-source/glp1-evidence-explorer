import streamlit as st
import requests
import json
import time

def extract_with_gemini(abstract):
    api_key = st.secrets["GEMINI_API_KEY"]

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3.8-flash:generateContent"
    )

    prompt = f"""
    You are extracting clinical trial evidence for a PharmD research project.

    Extract information ONLY from the abstract below.
    Do not invent missing values.

    Return a JSON object containing:
    - study_design
    - medications
    - doses
    - sample_size
    - duration
    - hba1c_results
    - weight_results
    - adverse_events

    Use null for information not reported.
    Preserve separate treatment arms and doses.
    Include exact supporting passages for numerical results.

    ABSTRACT:
    {abstract}
    """

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers={"x-goog-api-key": api_key},
                json={
                    "contents": [
                        {"parts": [{"text": prompt}]}
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                },
                timeout=90
            )

            if response.status_code in (429, 503):
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue

            response.raise_for_status()

            result = response.json()
            extracted_text = result["candidates"][0]["content"]["parts"][0]["text"]

            return json.loads(extracted_text)

        except (requests.RequestException, KeyError, ValueError) as error:
            if attempt == 2:
                return {"error": str(error)}

    return {"error": "Gemini is temporarily unavailable."}
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
