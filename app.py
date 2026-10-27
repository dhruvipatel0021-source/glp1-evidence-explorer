
import streamlit as st
import requests
import json
import time
import re

# ==========================================
# WEBSITE SETTINGS
# ==========================================

st.set_page_config(
    page_title="GLP-1 Evidence Explorer",
    page_icon="💊",
    layout="wide"
)

# ==========================================
# GEMINI AI EXTRACTION
# ==========================================

def extract_with_gemini(abstract):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return {
            "error": "Gemini API key missing from Streamlit Secrets."
        }

    prompt = f"""
You are extracting clinical trial evidence for a PharmD research project.

Use ONLY the provided abstract.
Do not invent missing results or values.

Return a valid JSON object with these fields:
- study_design
- medications
- doses
- sample_size
- duration
- hba1c_results
- weight_results
- adverse_events
- supporting_passages

Preserve separate treatment arms and doses.
Use null for missing information.
Provide short exact supporting passages for numerical results.
Do not make treatment recommendations.

ABSTRACT:
{abstract}
"""

    model = "gemini-3.8-flash"

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
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

                return {
                    "error": (
                        f"Gemini is temporarily unavailable "
                        f"(HTTP {response.status_code})."
                    )
                }

            if not response.ok:
                try:
                    message = response.json()["error"]["message"]
                except (ValueError, KeyError, TypeError):
                    message = response.text[:500]

                return {
                    "error": (
                        f"Gemini HTTP {response.status_code}: "
                        f"{message}"
                    )
                }

            result = response.json()

            parts = result["candidates"][0]["content"]["parts"]

            extracted_text = "".join(
                part.get("text", "") for part in parts
            )

            extracted = json.loads(extracted_text)

            if not isinstance(extracted, dict):
                return {
                    "error": "Gemini returned an unexpected JSON format."
                }

            extracted["ai_model"] = model

            return extracted

        except requests.RequestException as error:
            if attempt == 2:
                return {"error": str(error)}

        except (KeyError, IndexError, ValueError, TypeError) as error:
            return {
                "error": f"Could not parse Gemini response: {error}"
            }

    return {"error": "Gemini extraction failed."}


# ==========================================
# PUBMED SEARCH
# ==========================================

def search_pubmed(medications):

    drug_names = {
        "Ozempic (semaglutide)": "semaglutide",
        "Rybelsus (oral semaglutide)": "semaglutide",
        "Victoza (liraglutide)": "liraglutide",
        "Trulicity (dulaglutide)": "dulaglutide",
        "Mounjaro (tirzepatide)": "tirzepatide"
    }

    selected = list(
        dict.fromkeys(drug_names[med] for med in medications)
    )

    drug_query = " OR ".join(
        f'"{drug}"[Title/Abstract]' for drug in selected
    )

    query = (
        f"({drug_query}) AND "
        '"Diabetes Mellitus, Type 2"[MeSH Terms] AND '
        '"randomized controlled trial"[Publication Type]'
    )

    response = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": query,
            "retmax": 20,
            "retmode": "json",
            "sort": "relevance"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()["esearchresult"]["idlist"]


# ==========================================
# ABSTRACT RETRIEVAL
# ==========================================

def get_study(pmid):

    response = requests.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={
            "query": f"EXT_ID:{pmid} AND SRC:MED",
            "format": "json",
            "resultType": "core"
        },
        timeout=30
    )

    response.raise_for_status()

    records = response.json()["resultList"]["result"]

    if not records:
        return None

    record = records[0]

    abstract = re.sub(
        r"<[^>]+>",
        " ",
        record.get("abstractText") or ""
    )

    return {
        "pmid": pmid,
        "title": record.get("title", "Untitled study"),
        "abstract": abstract
    }


# ==========================================
# WEBSITE INTERFACE
# ==========================================

st.title("GLP-1 Evidence Explorer")

st.subheader(
    "AI-Assisted Clinical & Pharmacoeconomic Evaluation"
)

st.info(
    "Research prototype for educational use only. "
    "AI-extracted evidence must be independently verified."
)

# ------------------------------------------
# PATIENT INFORMATION
# ------------------------------------------

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
        [
            "Commercial",
            "Medicare",
            "Medicaid",
            "Uninsured"
        ]
    )

# ------------------------------------------
# MEDICATION SELECTION
# ------------------------------------------

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

# ------------------------------------------
# CLINICAL EVIDENCE SEARCH
# ------------------------------------------

st.header("3. Clinical Evidence Search")

if st.button("Compare Medications", type="primary"):

    if not medications:
        st.warning("Please select at least one medication.")

    else:

        try:
            with st.spinner("Searching PubMed..."):
                pmids = search_pubmed(medications)

            st.success(
                f"Retrieved {len(pmids)} PubMed records for review."
            )

            if not pmids:
                st.info("No matching studies were found.")

            else:

                st.subheader("PubMed Search Results")

                for pmid in pmids:
                    st.markdown(
                        f"- [PubMed PMID {pmid}]"
                        f"(https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
                    )

                st.subheader("4. AI-Extracted Clinical Evidence")

                st.caption(
                    "Testing AI extraction on the first three "
                    "PubMed results. Study eligibility and "
                    "extracted values have not yet been verified."
                )

                for pmid in pmids[:1]:

                    with st.expander(
                        f"Study PMID: {pmid}",
                        expanded=True
                    ):

                        try:
                            study = get_study(pmid)

                            if study is None:
                                st.warning("Study not found.")
                                continue

                            st.write(
                                "**Study:**",
                                study["title"]
                            )

                            st.markdown(
                                f"[View original PubMed record]"
                                f"(https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
                            )

                            if not study["abstract"]:
                                st.warning(
                                    "No abstract available for this study."
                                )
                                continue

                            with st.spinner(
                                "Gemini is extracting clinical outcomes..."
                            ):
                                extraction = extract_with_gemini(
                                    study["abstract"]
                                )

                            if "error" in extraction:
                                st.warning(
                                    "AI extraction unavailable: "
                                    + extraction["error"]
                                )

                            else:
                                st.json(extraction)

                                st.caption(
                                    "AI-generated extraction. "
                                    "Verify numerical results against "
                                    "the original publication."
                                )

                        except (
                            requests.RequestException,
                            KeyError,
                            IndexError,
                            ValueError
                        ) as error:
                            st.warning(
                                f"Could not process study: {error}"
                            )

        except (
            requests.RequestException,
            KeyError,
            ValueError
        ) as error:
            st.error(
                f"PubMed search failed: {error}"
            )


# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "GLP-1 Evidence Explorer | Research prototype | "
    "Not intended for clinical decision-making"
)
