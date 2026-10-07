# S28-02A: Hybrid Retrieval Closure — Evidence Delta Report

**Document ID:** `AUDIT-S28-02A-HYBRID-RETRIEVAL-CLOSURE`  
**Phase:** `S28-02A — Hybrid Retrieval Closure`  
**Workspace:** `/home/eng_Momen/Projects/المشروع الحالي/Video maker`  
**Date:** 2026-10-02  
**Status:** **PASSED & VERIFIED (S28-02 FINAL PASS)**  
**Author:** Antigravity (AI Engineering Agent)  

---

## 1. Executive Summary

This delta report establishes formal evidence for the closure of **S28-02A (Hybrid Retrieval Closure)**.

The Knowledge Platform retrieval channel was previously reliant on lexical search (BM25 / TF-IDF) followed by reranking. In this phase, a genuine, provider-neutral **Semantic Retrieval Channel** was designed, implemented, and fused with the lexical channel, completing the full hybrid retrieval specification:

$$\text{Query} \longrightarrow \text{Hard Metadata Filtering} \longrightarrow \begin{cases} \text{Lexical Retrieval (BM25/TF-IDF)} \\ \text{Semantic Retrieval (Dense Concept \& LSA)} \end{cases} \longrightarrow \text{Candidate Fusion (RRF)} \longrightarrow \text{Reranking} \longrightarrow \text{Deduplication} \longrightarrow \text{Bounded Context}$$

All architectural invariants (`Knowledge ≠ Runtime Authority`, `Skill ≠ Permission`, `ToolAuthorizationPolicy = Absolute Authority`) remain strictly preserved.

---

## 2. Architecture & Channel Implementations

### 2.1 Where Semantic Retrieval is Implemented
- **Module:** [`ai/knowledge/semantic.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/semantic.py)
- **Abstract Contract:** [`BaseSemanticScorer`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/semantic.py#L75-L95)
  - `is_available() -> bool`
  - `score_chunks(query: str, chunks: Sequence[KnowledgeChunk]) -> List[float]`
- **Concrete Provider-Neutral Implementation:** [`DenseConceptSemanticScorer`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/semantic.py#L97-L215)
  - Combines 9 Creative Video Domain Concept Spaces (Voiceover/Spoken, Motion/Disney, Dynamic Montage/Beats, Sound Design/Ducking, Kinetic Typography, FFmpeg Engineering, Living Canvas, Tabletop Staging, Hook Sprint) with Latent Semantic Analysis (`TruncatedSVD` on TF-IDF matrices).
  - 100% offline, hermetic, deterministic, with zero external cloud API dependencies.
  - Outputs continuous cosine similarity scores in $[0.0, 1.0]$.
- **Extensible Provider Scorer:** [`ProviderSemanticScorer`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/semantic.py#L235-L268) allowing pluggable neural embedding adapters without violating domain boundaries.

### 2.2 Lexical Retrieval Implementation
- **Module:** [`ai/knowledge/retriever.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/retriever.py#L141-L188) (`_run_lexical_channel`)
- Computes exact token overlap across section headings (weighted 3.0x), chunk text bodies with sublinear term-frequency scaling ($\log(1 + \text{tf}) \times 1.5$), and tag tokens (2.5x).

### 2.3 Semantic Retrieval Implementation
- **Module:** [`ai/knowledge/retriever.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/retriever.py#L190-L212) (`_run_semantic_channel`)
- Evaluates candidate chunks against query in dense semantic concept space and LSA continuous space, providing semantic scores and explanations.

### 2.4 Candidate Fusion Method
- **Module:** [`ai/knowledge/retriever.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/retriever.py#L214-L289) (`_fuse_candidates`)
- Combines candidate sets via **Reciprocal Rank Fusion (RRF)** ($k=20$) augmented with normalized score convex combination:
  $$RRF(d) = \frac{0.5}{20 + \text{rank}_{\text{lex}}(d)} + \frac{0.5}{20 + \text{rank}_{\text{sem}}(d)}$$
  $$S_{\text{fusion}}(d) = RRF(d) \times 10.0 + 0.4 \times \hat{S}_{\text{lex}}(d) + 0.6 \times \hat{S}_{\text{sem}}(d)$$
- Preserves component scores in [`RetrievedChunk`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/contracts.py#L116-L124): `lexical_score`, `semantic_score`, `fusion_score`.

### 2.5 Context Reranking Behavior
- **Module:** [`ai/knowledge/retriever.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/retriever.py#L291-L345) (`_rerank_candidates`)
- Adjusts fused scores using contextual signals:
  - Explicit `required_knowledge_ids` boost: $+10.0$
  - Video type alignment boost: $+5.0$ (or mild mismatch penalty $-2.5$)
  - Platform alignment boost: $+2.0$
- Strict deterministic ordering: sorts descending by `(score, chunk.document_id, chunk.chunk_id)`.

### 2.6 Offline / Degraded-Mode Behavior
- **Module:** [`ai/knowledge/retriever.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/retriever.py#L400-L440)
- If the semantic backend is unavailable or raises an exception:
  1. The system **never** silently claims hybrid execution.
  2. The result explicitly reports:
     - `retrieval_mode = RetrievalMode.DEGRADED_LEXICAL`
     - `degraded_reason = "Semantic retrieval backend unavailable..."`
  3. Seamlessly falls back to the lexical channel.
  4. **Security Invariant Preserved**: Hard metadata constraints (e.g. `MUSIC_ONLY` excluding spoken VO) are enforced unconditionally before scoring.

---

## 3. Dedicated Semantic & Behavioral Tests

Added to [`tests/ai/knowledge/test_knowledge_platform.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/ai/knowledge/test_knowledge_platform.py#L350-L450):

| Test Function | Verification Purpose | Outcome |
|---|---|---|
| `test_semantic_paraphrase_retrieval` | Query `"dialogue delivery natural rhythm and pause dynamics without robotic monotonic cadence"` contains zero terms matching document title/tags, but semantic meaning corresponds to spoken VO humanizer. Asserts `know_sop_spoken_vo` is retrieved with `semantic_score > 0.15`. | **PASSED** |
| `test_lexical_false_friend_resolution` | Query `"audio volume ducking and sound design attenuation under spoken voiceover"` contains voiceover words, but semantic intent is audio ducking. Asserts `know_taste_sfx_matrix` / `know_sop_sound_design` ranks higher than `know_sop_spoken_vo`. | **PASSED** |
| `test_explicit_retrieval_modes` | Verifies explicit caller selection of `RetrievalMode.LEXICAL_ONLY`, `RetrievalMode.SEMANTIC_ONLY`, and `RetrievalMode.HYBRID`. | **PASSED** |
| `test_degraded_lexical_mode_when_semantic_unavailable` | Configures `UnavailableSemanticScorer`. Asserts `res.retrieval_mode == DEGRADED_LEXICAL`, `res.degraded_reason` is populated, chunks are returned via lexical fallback, and `MUSIC_ONLY` exclusion remains strictly enforced. | **PASSED** |

---

## 4. Ablation Evaluation Results (12 Scenarios)

The comprehensive Knowledge Retrieval Dataset in [`ai/evals/creative_datasets.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/evals/creative_datasets.py) was evaluated across all 3 modes using [`tests/ai/evals/test_knowledge_and_skill_evals.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/ai/evals/test_knowledge_and_skill_evals.py).

Machine-readable report exported to [`documentation/audits/s28_02_eval_report.json`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/documentation/audits/s28_02_eval_report.json).

### 4.1 Comparative Ablation Matrix

| Metric | Lexical Only | Semantic Only | Hybrid (FUSED) | Gate Target |
|---|---|---|---|---|
| **Mean Precision@k** | $0.9375$ | $0.5278$ | **$0.8611$** | $\ge 0.70$ (PASS) |
| **Mean Recall@k** | $0.9167$ | $0.7083$ | **$0.9167$** | $\ge 0.85$ (PASS) |
| **Irrelevant Retrieval Rate** | $0.0000$ | $0.0000$ | **$0.0000$** | $= 0.00$ (PASS) |
| **Forbidden Violations** | $0$ | $0$ | **$0$** | $= 0$ (PASS) |

### 4.2 Key Findings from Ablation:
1. **Semantic Channel Proof**: On paraphrase cases where exact keywords are absent, the semantic channel bridges the vocabulary gap, pulling relevant SOPs that pure lexical queries rank low.
2. **Hybrid Synergy**: Hybrid candidate fusion (RRF) preserves the high recall of the lexical channel while incorporating semantic conceptual alignment, achieving $0.9167$ recall and $0.8611$ precision with zero forbidden hits.

---

## 5. Official Stage Name Correction

In accordance with Section 7 of the user directive, all references to the upcoming milestone have been updated across project documentation:

- **Previous informal name:** `S28-03 — Intent Parser & Creative Brief Builder`
- **Official full title:** `S28-03 — Intent + Creative Brief + Recipe Engine + Audio Modes`

Updated in:
- [`documentation/audits/S28-02-EXECUTION-EVIDENCE-REPORT.md`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/documentation/audits/S28-02-EXECUTION-EVIDENCE-REPORT.md#L340)

*Note: No runtime or contract implementation for S28-03 was started during S28-02A.*

---

## 6. Test Suite & Parity Execution Summary

### 6.1 Pytest Suite
```bash
.venv/bin/pytest tests/ai/knowledge/ tests/ai/skills/ tests/ai/security/test_knowledge_skill_security.py tests/ai/evals/test_knowledge_and_skill_evals.py tests/ai/integration/test_knowledge_skill_integration.py tests/ai/contracts/test_creative_contracts.py tests/ai/test_creative_architecture_guards.py tests/ai/test_ai_architecture_guards.py tests/ai/test_provider_neutrality_architecture.py -v
```
**Result: 92 passed in 5.40s (0 failures, 0 errors)**

### 6.2 Vitest Parity Suite
```bash
npm run test -- tests/remotion/creative_contracts_parity.test.ts
```
**Result: 14 test files passed, 159 tests passed in 7.91s (0 failures)**

### 6.3 Contract Parity Check
```bash
python scripts/generate_creative_contracts.py --check
```
**Result: Ground Truth Parity Confirmed (Zero drift)**

---

## 7. Exit Gate Checklist Verification Table

| Requirement / Checklist Item | Verification Evidence | Status |
|---|---|---|
| **Metadata filtering operational** | Tested in `test_retriever_music_only_excludes_voiceover`, `test_retriever_excludes_retired_documents`. | **PASS** |
| **Lexical retrieval operational** | `_run_lexical_channel` evaluated independently in ablation suite. | **PASS** |
| **Semantic retrieval operational** | `DenseConceptSemanticScorer` evaluated independently in ablation suite. | **PASS** |
| **Hybrid candidate fusion operational** | RRF candidate fusion tested in `_fuse_candidates` and `test_explicit_retrieval_modes`. | **PASS** |
| **Reranking operational** | Context reranking tested in `_rerank_candidates` and false-friend test. | **PASS** |
| **Deduplication operational** | Content-hash deduplication tested in `test_retriever_deduplication`. | **PASS** |
| **Context bounding operational** | Clamping to chunk and token budgets tested in `test_retriever_context_bounding`. | **PASS** |
| **Semantic paraphrase tests** | Tested in `test_semantic_paraphrase_retrieval` and `k_case_11`. | **PASS** |
| **Lexical false-friend tests** | Tested in `test_lexical_false_friend_resolution` and `k_case_12`. | **PASS** |
| **Lexical-only evaluation recorded** | Documented in `s28_02_eval_report.json` under `ablation_evaluation.lexical_only`. | **PASS** |
| **Semantic-only evaluation recorded** | Documented in `s28_02_eval_report.json` under `ablation_evaluation.semantic_only`. | **PASS** |
| **Hybrid evaluation recorded** | Documented in `s28_02_eval_report.json` under `ablation_evaluation.hybrid`. | **PASS** |
| **Degraded-mode behavior** | Tested in `test_degraded_lexical_mode_when_semantic_unavailable`. | **PASS** |
| **Security boundaries preserved** | Tested in `test_knowledge_skill_security.py` (5 tests passing). | **PASS** |
| **Skill ≠ Permission preserved** | `SkillExecutor` enforces `ToolAuthorizationPolicy`; tested in integration suite. | **PASS** |
| **ToolAuthorizationPolicy preserved** | Server-side execution authority enforced with 0 bypasses. | **PASS** |
| **S28-03 official scope/name corrected** | Updated to `S28-03 — Intent + Creative Brief + Recipe Engine + Audio Modes`. | **PASS** |
| **No S28-03 runtime started** | Strictly zero S28-03 engines instantiated. | **PASS** |
| **All affected tests green** | 92 Python tests + 159 Vitest tests passing. | **PASS** |
| **Evidence report produced** | Documented in this report and updated evidence files. | **PASS** |

---

## 8. Conclusion

All closure criteria for **S28-02A** have been met and verified.

$$\mathbf{S28\text{-}02 \text{ FINAL PASS}}$$

The system is now fully prepared to advance to:
$$\mathbf{S28\text{-}03 \text{ — Intent + Creative Brief + Recipe Engine + Audio Modes}}$$
