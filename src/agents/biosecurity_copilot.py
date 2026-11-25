"""Guardrailed LangGraph Biosecurity Compliance Copilot with hybrid BM25 + TF-IDF
retrieval over Defra BTOM, IPAFFS, UK Phytosanitary Manuals, and FSA Food Law,
plus a citation-verifier judge node and deterministic 8-digit HS-code fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

import numpy as np
from langgraph.graph import END, StateGraph
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class RegulatoryDocument:
    """Authoritative UK Defra BTOM / APHA / FSA regulatory corpus passage."""

    doc_id: str
    title: str
    source: str
    risk_scope: str
    text: str


REGULATORY_CORPUS: tuple[RegulatoryDocument, ...] = (
    RegulatoryDocument(
        doc_id="BTOM-HIGH-01",
        title="Defra BTOM High SPS Risk Category — Live Animals & Germinal Products",
        source="Defra Border Target Operating Model (BTOM) Guidance",
        risk_scope="High",
        text=(
            "Under the Defra Border Target Operating Model (BTOM), High-risk SPS consignments "
            "including live animals, germinal products, and high-risk plants for planting "
            "(such as seed potatoes HS 07011000 and regulated nursery stock HS 06029099) "
            "require mandatory IPAFFS pre-notification at least 24 hours prior to arrival, "
            "an Export Health Certificate (EHC) or Phytosanitary Certificate, and 100% "
            "documentary, identity, and physical inspection at a designated UK Border Control Post (BCP)."
        ),
    ),
    RegulatoryDocument(
        doc_id="BTOM-MED-02",
        title="Defra BTOM Medium SPS Risk Category — POAO, Beef, Poultry, Dairy & Salmon",
        source="Defra Border Target Operating Model (BTOM) POAO Risk Tables",
        risk_scope="Medium",
        text=(
            "Medium-risk Products of Animal Origin (POAO) under BTOM—including fresh or chilled "
            "boneless beef (HS 02013000), poultry meat cuts (HS 02071410), Atlantic salmon (HS 03021400), "
            "and unpasteurised/chilled dairy cheese (HS 04069099)—require an official Export Health "
            "Certificate (EHC), IPAFFS CHED-P pre-notification before Great Britain port arrival, "
            "and risk-based identity and physical checks (1% to 30% depending on commodity and origin)."
        ),
    ),
    RegulatoryDocument(
        doc_id="BTOM-LOW-03",
        title="Defra BTOM Low SPS Risk Category — Grains, Oilseeds & Low-Risk Produce",
        source="Defra BTOM Plant & Commodity Risk Matrix",
        risk_scope="Low",
        text=(
            "Low-risk BTOM commodities such as milling wheat (HS 10019900), oilseed rape (HS 12051090), "
            "and certain processed fruit and vegetables (e.g., apples HS 08081080 from low-risk EU origins) "
            "do not require a routine Export Health Certificate or routine BCP physical inspection, "
            "though commercial invoices and IPAFFS pre-notification may apply to composite or regulated "
            "plant consignments, and intelligence-led surveillance checks remain active."
        ),
    ),
    RegulatoryDocument(
        doc_id="IPAFFS-04",
        title="IPAFFS Pre-Notification & CHED Documentary Workflow",
        source="Defra & APHA IPAFFS Operational Manual",
        risk_scope="Medium",
        text=(
            "Importers into Great Britain must submit a Common Health Entry Document via IPAFFS "
            "(CHED-A for live animals, CHED-P for POAO, CHED-PP for plants and plant products) "
            "using the exact 8-digit CN/HS commodity code and valid UK EORI number. Failure to "
            "pre-notify via IPAFFS or mismatched EHC/Phytosanitary serial numbers results in port "
            "holds, clearance delays, or statutory re-export/destruction notices."
        ),
    ),
    RegulatoryDocument(
        doc_id="PHYTO-05",
        title="UK Phytosanitary Manual — Quarantine Pests, Soil & Potatoes",
        source="Defra / APHA UK Plant Health & Phytosanitary Manual",
        risk_scope="High",
        text=(
            "The UK Phytosanitary Manual enforces strict quarantine controls against Xylella fastidiosa, "
            "Ralstonia solanacearum (brown rot), and Epitrix flea beetles on ware potatoes (HS 07019090) "
            "and fresh tomatoes (HS 07020000) from pest-endemic zones. Imports of soil and growing "
            "medium attached to plants from third countries are prohibited unless certified pest-free "
            "with an official Phytosanitary Certificate and inspected under CHED-PP."
        ),
    ),
    RegulatoryDocument(
        doc_id="FSA-LAW-06",
        title="FSA Food Law — Allergen Labelling (Natasha's Law) & Mandatory Recalls",
        source="Food Standards Agency (FSA) Food Law Code of Practice",
        risk_scope="Medium",
        text=(
            "Under UK Food Standards Agency (FSA) Food Law, Retained Regulation (EC) 178/2002 "
            "Articles 14 and 19, and the Food Information (Amendment) Regulations 2019 (Natasha's Law), "
            "importers and food business operators must declare all 14 statutory allergens on "
            "prepacked for direct sale (PPDS) and wholesale consignments, maintain one-step-back/"
            "one-step-forward traceability, and immediately withdraw/recall unsafe or contaminated "
            "(e.g., mycotoxin, Salmonella, undeclared allergen) food while notifying the FSA and Port Health Authority."
        ),
    ),
)

# Deterministic 8-digit HS/CN code -> Defra BTOM & FSA regulatory lookup
HS_CODE_BTOM_REGISTRY: dict[str, dict[str, str]] = {
    "07011000": {
        "commodity": "Seed potatoes (fresh or chilled)",
        "btom_risk_tier": "High",
        "ched_type": "CHED-PP",
        "ipaffs_required": "Yes (24h prior)",
        "certificate_required": "Phytosanitary Certificate + UK quarantine clearance",
        "authority": "Defra / APHA Plant Health",
        "doc_id": "BTOM-HIGH-01",
    },
    "06029099": {
        "commodity": "Live plants for planting (nursery stock)",
        "btom_risk_tier": "High",
        "ched_type": "CHED-PP",
        "ipaffs_required": "Yes (24h prior)",
        "certificate_required": "Phytosanitary Certificate (Xylella-free attestation)",
        "authority": "Defra / APHA Plant Health",
        "doc_id": "BTOM-HIGH-01",
    },
    "02013000": {
        "commodity": "Fresh or chilled boneless bovine meat",
        "btom_risk_tier": "Medium",
        "ched_type": "CHED-P",
        "ipaffs_required": "Yes (prior to GB arrival)",
        "certificate_required": "Export Health Certificate (EHC)",
        "authority": "Defra / Port Health Authority (FSA)",
        "doc_id": "BTOM-MED-02",
    },
    "02071410": {
        "commodity": "Frozen boneless poultry cuts",
        "btom_risk_tier": "Medium",
        "ched_type": "CHED-P",
        "ipaffs_required": "Yes (prior to GB arrival)",
        "certificate_required": "Export Health Certificate (EHC)",
        "authority": "Defra / Port Health Authority (FSA)",
        "doc_id": "BTOM-MED-02",
    },
    "03021400": {
        "commodity": "Fresh or chilled Atlantic salmon",
        "btom_risk_tier": "Medium",
        "ched_type": "CHED-P",
        "ipaffs_required": "Yes (prior to GB arrival)",
        "certificate_required": "Export Health Certificate (EHC) + IUU Catch Certificate",
        "authority": "Defra / Port Health Authority (FSA)",
        "doc_id": "BTOM-MED-02",
    },
    "04069099": {
        "commodity": "Dairy cheese and curd products",
        "btom_risk_tier": "Medium",
        "ched_type": "CHED-P",
        "ipaffs_required": "Yes (prior to GB arrival)",
        "certificate_required": "Export Health Certificate (EHC) + FSA allergen trace",
        "authority": "Defra / FSA Port Health",
        "doc_id": "BTOM-MED-02",
    },
    "07019090": {
        "commodity": "Ware potatoes (fresh or chilled)",
        "btom_risk_tier": "Medium",
        "ched_type": "CHED-PP",
        "ipaffs_required": "Yes (CHED-PP prior notification)",
        "certificate_required": "Phytosanitary Certificate (Ralstonia/Epitrix checks)",
        "authority": "Defra / APHA Plant Health",
        "doc_id": "PHYTO-05",
    },
    "07020000": {
        "commodity": "Fresh or chilled tomatoes",
        "btom_risk_tier": "Medium",
        "ched_type": "CHED-PP",
        "ipaffs_required": "Yes (origin-dependent host checks)",
        "certificate_required": "Phytosanitary Certificate (if regulated origin)",
        "authority": "Defra / APHA Plant Health",
        "doc_id": "PHYTO-05",
    },
    "08081080": {
        "commodity": "Fresh apples",
        "btom_risk_tier": "Low",
        "ched_type": "None (EU low-risk) / CHED-PP (RoW)",
        "ipaffs_required": "Origin-dependent",
        "certificate_required": "None for EU low-risk; Phytosanitary for RoW",
        "authority": "Defra / APHA",
        "doc_id": "BTOM-LOW-03",
    },
    "10019900": {
        "commodity": "Milling wheat and meslin",
        "btom_risk_tier": "Low",
        "ched_type": "None (routine low-risk)",
        "ipaffs_required": "No routine CHED; FSA mycotoxin surveillance applies",
        "certificate_required": "Commercial invoice & FSA traceability record",
        "authority": "Defra / FSA",
        "doc_id": "BTOM-LOW-03",
    },
    "12051090": {
        "commodity": "Low erucic acid rape or colza seeds (oilseed rape)",
        "btom_risk_tier": "Low",
        "ched_type": "None (routine low-risk)",
        "ipaffs_required": "No routine CHED",
        "certificate_required": "Commercial invoice & origin declaration",
        "authority": "Defra",
        "doc_id": "BTOM-LOW-03",
    },
}

UNSAFE_BYPASS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+(ipaffs|btom|bcp|customs|border|inspection)\b", re.IGNORECASE),
    re.compile(r"\bforge\s+(ehc|certificate|phytosanitary|ched)\b", re.IGNORECASE),
    re.compile(r"\bsmuggle\b", re.IGNORECASE),
)


def lookup_hs_btom_tier(hs_code: str | None) -> dict[str, str] | None:
    """Deterministic 8-digit HS-code lookup for Defra BTOM SPS risk tier."""
    if not hs_code:
        return None
    normalized = re.sub(r"\D", "", str(hs_code))
    if len(normalized) != 8:
        return None
    if normalized in HS_CODE_BTOM_REGISTRY:
        return {"hs_code": normalized, **HS_CODE_BTOM_REGISTRY[normalized]}

    # Chapter-level deterministic fallback when exact 8-digit code is uncatalogued
    chapter = normalized[:2]
    if chapter in {"01"}:
        tier, ched, doc = "High", "CHED-A", "BTOM-HIGH-01"
    elif chapter in {"02", "03", "04", "16"}:
        tier, ched, doc = "Medium", "CHED-P", "BTOM-MED-02"
    elif chapter in {"06", "07"}:
        tier, ched, doc = "Medium", "CHED-PP", "PHYTO-05"
    elif chapter in {"10", "11", "12"}:
        tier, ched, doc = "Low", "None (routine low-risk)", "BTOM-LOW-03"
    else:
        return None

    return {
        "hs_code": normalized,
        "commodity": f"Uncatalogued HS Chapter {chapter} agri-food product",
        "btom_risk_tier": tier,
        "ched_type": ched,
        "ipaffs_required": "Yes" if tier in {"High", "Medium"} else "Check Defra tariff",
        "certificate_required": (
            "EHC / Phytosanitary Certificate" if tier in {"High", "Medium"} else "Commercial invoice"
        ),
        "authority": "Defra / APHA / FSA",
        "doc_id": doc,
    }


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class HybridRegulatoryRetriever:
    """Hybrid BM25Okapi + TF-IDF cosine retriever over UK biosecurity & FSA texts."""

    def __init__(self, docs: tuple[RegulatoryDocument, ...] = REGULATORY_CORPUS) -> None:
        self.docs = docs
        tokenized_corpus = [_tokenize(f"{d.title} {d.source} {d.text}") for d in docs]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.tfidf = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.tfidf_matrix = self.tfidf.fit_transform(
            [f"{d.title} {d.source} {d.text}" for d in docs]
        )

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, object]]:
        tokens = _tokenize(query)
        if not tokens:
            return []

        bm25_scores = np.asarray(self.bm25.get_scores(tokens), dtype=float)
        bm25_scaled = np.tanh(np.maximum(bm25_scores, 0.0) / 4.5)

        q_vec = self.tfidf.transform([query])
        tfidf_scores = cosine_similarity(q_vec, self.tfidf_matrix).ravel()

        hybrid_scores = np.where(
            (bm25_scores > 0.0) | (tfidf_scores > 0.05),
            0.55 * bm25_scaled + 0.45 * tfidf_scores,
            0.0,
        )

        ranked_indices = np.argsort(hybrid_scores)[::-1][:top_k]
        results: list[dict[str, object]] = []
        for idx in ranked_indices:
            score = float(hybrid_scores[idx])
            if score <= 0.0:
                continue
            doc = self.docs[int(idx)]
            results.append(
                {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "source": doc.source,
                    "risk_scope": doc.risk_scope,
                    "text": doc.text,
                    "hybrid_score": round(score, 4),
                    "bm25_raw": round(float(bm25_scores[idx]), 4),
                    "tfidf_raw": round(float(tfidf_scores[idx]), 4),
                }
            )
        return results


class CopilotState(TypedDict, total=False):
    """LangGraph workflow state for border biosecurity compliance copilot."""

    query: str
    hs_code: str | None
    origin_country: str
    blocked: bool
    block_reason: str
    extracted_hs_code: str | None
    hs_lookup: dict[str, str] | None
    retrieved_docs: list[dict[str, object]]
    draft_answer: str
    citations: list[str]
    btom_risk_tier: str
    citations_verified: bool
    verification_notes: str
    used_deterministic_fallback: bool
    final_answer: str


class BiosecurityCopilot:
    """Guardrailed LangGraph compliance copilot with hybrid retrieval,
    citation-verifier judge node, and deterministic HS-code fallback.
    """

    def __init__(self, min_retrieval_score: float = 0.25) -> None:
        self.retriever = HybridRegulatoryRetriever()
        self.min_retrieval_score = min_retrieval_score
        self.graph = self._compile_graph()

    def _guardrail_node(self, state: CopilotState) -> CopilotState:
        query = (state.get("query") or "").strip()
        explicit_hs = state.get("hs_code")

        if not query and not explicit_hs:
            return {
                "blocked": True,
                "block_reason": "Empty compliance query and no 8-digit HS code provided.",
                "btom_risk_tier": "Unknown",
                "citations": [],
                "citations_verified": False,
                "used_deterministic_fallback": False,
                "final_answer": (
                    "Please provide a UK border biosecurity question or an 8-digit CN/HS commodity code."
                ),
            }

        for pattern in UNSAFE_BYPASS_PATTERNS:
            if pattern.search(query):
                return {
                    "blocked": True,
                    "block_reason": "Compliance guardrail triggered: cannot assist with bypassing border controls or forging certificates.",
                    "btom_risk_tier": "Restricted",
                    "citations": [],
                    "citations_verified": True,
                    "used_deterministic_fallback": False,
                    "final_answer": (
                        "Request blocked by HarvestShield UK biosecurity guardrail. "
                        "I cannot provide guidance on bypassing IPAFFS, Defra BTOM inspections, "
                        "or falsifying Export Health / Phytosanitary Certificates."
                    ),
                }

        hs_match = re.search(r"\b(\d{8})\b", query)
        resolved_hs = explicit_hs or (hs_match.group(1) if hs_match else None)
        hs_lookup = lookup_hs_btom_tier(resolved_hs)
        return {
            "blocked": False,
            "extracted_hs_code": resolved_hs,
            "hs_lookup": hs_lookup,
        }

    def _retrieve_node(self, state: CopilotState) -> CopilotState:
        query = state.get("query") or ""
        docs = self.retriever.retrieve(query, top_k=3)
        return {"retrieved_docs": docs}

    def _draft_node(self, state: CopilotState) -> CopilotState:
        docs = state.get("retrieved_docs") or []
        hs_lookup = state.get("hs_lookup")

        if not docs or float(docs[0]["hybrid_score"]) < self.min_retrieval_score:
            return {
                "draft_answer": "",
                "citations": [],
                "btom_risk_tier": hs_lookup["btom_risk_tier"] if hs_lookup else "Unknown",
            }

        top_doc = docs[0]
        citations = [str(d["doc_id"]) for d in docs]
        risk_tier = hs_lookup["btom_risk_tier"] if hs_lookup else str(top_doc["risk_scope"])

        parts: list[str] = []
        if hs_lookup:
            parts.append(
                f"HS {hs_lookup['hs_code']} ({hs_lookup['commodity']}) is classified as "
                f"**{hs_lookup['btom_risk_tier']} BTOM SPS Risk** ({hs_lookup['ched_type']}, "
                f"IPAFFS: {hs_lookup['ipaffs_required']}, Certificate: {hs_lookup['certificate_required']}) "
                f"[{hs_lookup['doc_id']}]."
            )

        for doc in docs[:2]:
            parts.append(f"{doc['title']}: {doc['text']} [{doc['doc_id']}]")

        return {
            "draft_answer": "\n\n".join(parts),
            "citations": citations,
            "btom_risk_tier": risk_tier,
        }

    def _citation_verifier_node(self, state: CopilotState) -> CopilotState:
        """Judge node verifying every cited [DOC-ID] is grounded in retrieved evidence
        and agrees with deterministic HS risk classification.
        """
        draft = state.get("draft_answer") or ""
        docs = state.get("retrieved_docs") or []
        hs_lookup = state.get("hs_lookup")
        retrieved_ids = {str(d["doc_id"]) for d in docs}
        cited_in_text = set(re.findall(r"\[([A-Z0-9-]+)\]", draft))

        if not draft or not cited_in_text:
            return {
                "citations_verified": False,
                "verification_notes": "No grounded citations in draft; invoking deterministic fallback.",
            }

        hallucinated = cited_in_text - retrieved_ids
        if hallucinated:
            return {
                "citations_verified": False,
                "verification_notes": f"Hallucinated citations detected: {sorted(hallucinated)}.",
            }

        if hs_lookup and hs_lookup["btom_risk_tier"] not in draft:
            return {
                "citations_verified": False,
                "verification_notes": "Draft omitted deterministic BTOM tier for HS code.",
            }

        return {
            "citations_verified": True,
            "verification_notes": f"Verified {len(cited_in_text)} grounded regulatory citations.",
            "used_deterministic_fallback": False,
            "final_answer": draft,
        }

    def _deterministic_fallback_node(self, state: CopilotState) -> CopilotState:
        """Deterministic 8-digit HS-code BTOM lookup fallback when RAG evidence is weak
        or citation verification fails.
        """
        hs_lookup = state.get("hs_lookup")
        hs_code = state.get("extracted_hs_code")
        if hs_lookup:
            doc_id = hs_lookup["doc_id"]
            msg = (
                f"[Deterministic BTOM HS-Code Lookup] HS {hs_lookup['hs_code']} "
                f"({hs_lookup['commodity']}): BTOM Risk Tier = **{hs_lookup['btom_risk_tier']}** | "
                f"CHED = {hs_lookup['ched_type']} | IPAFFS = {hs_lookup['ipaffs_required']} | "
                f"Certificates = {hs_lookup['certificate_required']} | "
                f"Authority = {hs_lookup['authority']} [{doc_id}]."
            )
            return {
                "used_deterministic_fallback": True,
                "btom_risk_tier": hs_lookup["btom_risk_tier"],
                "citations": [doc_id],
                "citations_verified": True,
                "final_answer": msg,
            }

        msg = (
            f"[Deterministic BTOM Fallback] No verified regulatory match found"
            f"{f' for HS {hs_code}' if hs_code else ''}. "
            "Consult Defra IPAFFS commodity lookup and UK Trade Tariff (8-digit CN code) "
            "before dispatch [IPAFFS-04]."
        )
        return {
            "used_deterministic_fallback": True,
            "btom_risk_tier": "Unknown",
            "citations": ["IPAFFS-04"],
            "citations_verified": True,
            "final_answer": msg,
        }

    def _compile_graph(self):
        graph = StateGraph(CopilotState)
        graph.add_node("guardrail", self._guardrail_node)
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("draft", self._draft_node)
        graph.add_node("verify_citations", self._citation_verifier_node)
        graph.add_node("deterministic_fallback", self._deterministic_fallback_node)

        graph.set_entry_point("guardrail")
        graph.add_conditional_edges(
            "guardrail",
            lambda s: "blocked" if s.get("blocked") else "proceed",
            {"blocked": END, "proceed": "retrieve"},
        )
        graph.add_edge("retrieve", "draft")
        graph.add_edge("draft", "verify_citations")
        graph.add_conditional_edges(
            "verify_citations",
            lambda s: "verified" if s.get("citations_verified") else "fallback",
            {"verified": END, "fallback": "deterministic_fallback"},
        )
        graph.add_edge("deterministic_fallback", END)
        return graph.compile()

    def ask(
        self,
        query: str,
        hs_code: str | None = None,
        origin_country: str = "EU",
    ) -> dict[str, object]:
        """Run the guardrailed LangGraph compliance workflow and return structured guidance."""
        result = self.graph.invoke(
            {
                "query": query,
                "hs_code": hs_code,
                "origin_country": origin_country,
            }
        )
        return {
            "answer": result.get("final_answer", ""),
            "btom_risk_tier": result.get("btom_risk_tier", "Unknown"),
            "hs_code": result.get("extracted_hs_code"),
            "citations": result.get("citations", []),
            "citations_verified": bool(result.get("citations_verified", False)),
            "verification_notes": result.get("verification_notes", ""),
            "used_deterministic_fallback": bool(result.get("used_deterministic_fallback", False)),
            "blocked": bool(result.get("blocked", False)),
            "block_reason": result.get("block_reason", ""),
        }
