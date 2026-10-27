
import streamlit as st
import requests
import json
import time
import re

st.set_page_config(
    page_title="GLP-1 Evidence Explorer",
    page_icon="💊",
    layout="wide"
)

# ----------------------------
# Gemini AI extraction
# ----------------------------

def extract_with_gemini(abstract):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return {"error": "Gemini API key is missing from Streamlit Secrets."}

    prompt = f"""
You are extracting evidence for a PharmD research project.

Use ONLY the abstract below. Do not invent results.

Return a JSON object with:
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
Include short exact source passages supporting numerical results.
Do not give treatment recommendations.

ABSTRACT:
{abstract}
"""

    # Models can become unavailable or overloaded.
    # Try the newer model first.
    models = ["gemini-3.8-flash"]

    last_error = "No available Gemini model responded."

    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent"
        )

        for attempt in range(2):
            try:
                response = requests.post(
                    url,
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "contents": [
                            {"parts": [{"text": prompt}]}
                        ],
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    },
                    timeout=60
                )

                if response.status_code in (429, 503):
                    last_error = (
                        f"{model}: HTTP {response.status_code} "
                        "(rate limit or high demand)"
                    )
                    if attempt == 0:
                        time.sleep(3)
                        continue
                    break

                if response.status_code in (400, 404):
    return {
        "error": (
            f"Gemini returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )
    }
                    last_error = f"{model}: model unavailable"
                    break

                response.raise_for_status()

                result = response.json()
                parts = result["candidates"][0]["content"]["parts"]
                extracted_text = "".join(
                    part.get("text", "") for part in parts
                )

                extracted = json.loads(extracted_text)

                if not isinstance(extracted, dict):
                    return {"error": "Gemini returned an unexpected format."}

                extracted["ai_model"] = model
                return extracted

            except (
                requests.RequestException,
                KeyError,
                IndexError,
                ValueError
            ) as error:
                last_error = str(error)
                break

    return {"error": last_error}


# ----------------------------
# PubMed search
# ----------------------------

def search_pubmed(medications):
    drug_names = {
        "Ozempic (semaglutide)": "semaglutide",
        "Rybelsus (oral semaglutide)": "semaglutide",
        "Victoza (liraglutide)": "liraglutide",
        "Trulicity (dulaglutide)": "dulaglutide",
        "Mounjaro (tirzepatide)": "tirzepatide"
    }

    selected = list(dict.fromkeys(
        drug_names[med] for med in medications
    ))

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


# ----------------------------
# Retrieve study abstract
# ----------------------------

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

    return {
        "pmid": pmid,
        "title": record.get("title", "Untitled study"),
        "abstract": re.sub(
            r"<[^>]+>", " ",
            record.get("abstractText", "")
        )
    }


# ----------------------------
# Website interface
# ----------------------------

st.title("GLP-1 Evidence Explorer")
st.subheader("AI-Assisted Clinical & Pharmacoeconomic Evaluation")

st.info(
    "Research prototype for educational use only. "
    "AI-extracted evidence requires verification."
)

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
                    "Testing automatic extraction on the first "
                    "3 search results. These studies have not yet "
                    "been manually screened for eligibility."
                )

                for pmid in pmids[:3]:

                    with st.expander(
                        f"Study PMID: {pmid}",
                        expanded=True
                    ):

                        try:
                            study = get_study(pmid)

                            if not study:
                                st.warning("Study record not found.")
                                continue

                            st.write("**Study:**", study["title"])

                            st.markdown(
                                f"[View original PubMed record]"
                                f"(https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
                            )

                            if not study["abstract"]:
                                st.warning("No abstract available.")
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
                                    "Unverified AI extraction. "
                                    "Check all values against the "
                                    "original publication."
                                )

                        except (
                            requests.RequestException,
                            KeyError,
                            IndexError
                        ) as error:
                            st.warning(
                                f"Could not process study: {error}"
                            )

        except (requests.RequestException, KeyError) as error:
            st.error(f"PubMed search failed: {error}")


st.divider()

st.caption(
    "GLP-1 Evidence Explorer | Research prototype | "
    "Not intended for clinical decision-making"
)
