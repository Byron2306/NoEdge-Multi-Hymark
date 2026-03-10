# Novelty Report: NoEdge-Multi-Hymark (HOMS v3.0)

## Assessment of Originality, Innovation, and Research Contribution

**System Name:** NoEdge-Multi-Hymark / HOMS v3.0  
**Institution:** North-West University (NWU), South Africa  
**Domain:** Educational Technology, Automated Assessment, AI in Education  
**Report Date:** March 2026

---

## Table of Contents

1. [Introduction and Scope](#1-introduction-and-scope)
2. [Prior Art and State of the Field](#2-prior-art-and-state-of-the-field)
3. [Novel Contributions of HOMS v3.0](#3-novel-contributions-of-homs-v30)
4. [Feature-by-Feature Novelty Analysis](#4-feature-by-feature-novelty-analysis)
5. [Comparative Analysis vs. Existing Systems](#5-comparative-analysis-vs-existing-systems)
6. [Limitations on Novelty Claims](#6-limitations-on-novelty-claims)
7. [Summary Novelty Matrix](#7-summary-novelty-matrix)
8. [Recommendations for Future Work](#8-recommendations-for-future-work)

---

## 1. Introduction and Scope

This report assesses the degree of novelty present in the NoEdge-Multi-Hymark system (HOMS v3.0). Novelty is evaluated across the following dimensions:

- **Technical novelty**: Does the system introduce new algorithms, architectures, or technical approaches not previously documented?
- **Combinatorial novelty**: Does the system combine existing technologies in a new or non-obvious way?
- **Applied novelty**: Does the system address a real-world problem in a domain where automated solutions are immature or absent?
- **Methodological novelty**: Does the system introduce new workflows or processes that advance academic practice?

The assessment is grounded in a review of related work in automated program assessment (APA), AI-powered grading, plagiarism detection, and LMS integration.

---

## 2. Prior Art and State of the Field

### 2.1 Automated Program Assessment (APA)

Automated assessment of programming assignments has been studied since the 1960s. The primary paradigm is **unit-test-based grading**: systems like **BOSS** (University of Warwick), **Web-CAT**, **Gradescope** (Turnitin), **CodeGrade**, and **Mimir** submit student code to hidden test cases and report pass/fail counts. While effective for correctness checking, these systems:

- Cannot assess *how* a solution was constructed (algorithmic approach, intermediate steps).
- Cannot provide rubric-weighted partial credit without heavy test engineering.
- Are fragile to minor output formatting differences.
- Do not produce human-quality natural language feedback.

### 2.2 Reference-Based Assessment (PyBryt)

Microsoft Research released **PyBryt** (2021) as an alternative paradigm: instead of testing outputs, it records and checks a student's runtime memory trace against annotations placed in a *reference implementation* (a model solution). This enables checking for specific intermediate values, algorithmic patterns, and data structure usage. HOMS v3.0 builds on top of PyBryt.

### 2.3 AI / LLM-Based Grading

Since 2022, several research systems and commercial products have applied Large Language Models to assignment grading:
- **GPT-4 for grading** essays has been validated in research (Mizumoto & Eguchi, 2023; Yan et al., 2024) with moderate agreement with human raters.
- **Gradescope AI** (Turnitin) uses NLP for answer grouping.
- **Cognii** provides dialogue-based AI assessment.
- None publicly document integration with Sakai/eFundi for grade round-trip automation.

### 2.4 LMS Integration

**Sakai** (on which eFundi is based) has a Gradebook API, but automated feedback upload via the ZIP mechanism is institution-specific and not standardised. Most published APA systems require manual grade export/import. Fully automated Playwright-driven feedback submission to a Sakai instance is not described in the reviewed literature.

### 2.5 Plagiarism Detection in Code

Systems such as **MOSS** (Stanford), **JPlag**, and **Dolos** compare code text or ASTs for similarity. None use annotation-vector-based behavioural similarity as implemented in HOMS.

---

## 3. Novel Contributions of HOMS v3.0

### 3.1 Contribution 1: Dual-Mode Hybrid Architecture (Offline + Cloud AI)

**Claim:** HOMS v3.0 is the first documented system to combine *offline PyBryt reference-based code assessment* with *cloud GPT AI natural-language assessment* within a single unified platform, sharing common LMS integration, feedback packaging, and moderation infrastructure.

**Significance:** This hybrid design is particularly valuable in resource-constrained university environments (intermittent connectivity, limited GPU resources) where neither pure offline nor pure cloud approaches are sufficient. The offline mode handles structured programming submissions without any API costs or connectivity requirements; the cloud mode handles unstructured written submissions that require semantic understanding beyond pattern matching.

**Prior art gap:** No reviewed system combines PyBryt with GPT-based grading in a single deployable unit.

---

### 3.2 Contribution 2: Annotation-Vector-Based Plagiarism Detection

**Claim:** The ModerationAgent implements a novel plagiarism detection approach based on *annotation pass/fail vectors* — the binary record of which PyBryt annotations were satisfied by each student's submission.

**Technical Detail:** For each pair of submissions `(A, B)`, the similarity score is:
```
similarity(A, B) = |{annotations: both_same_outcome}| / total_annotations
```

**Why this is novel:** Traditional code plagiarism detectors (MOSS, JPlag, Dolos) compare lexical tokens, AST structure, or control flow graphs. These are defeated by variable renaming, code restructuring, or loop/conditional reordering. Annotation-vector similarity measures *behavioural equivalence* at the algorithmic level — two genuinely independent correct solutions will have high similarity, but this is expected and correct. The key insight is that *identical incorrect patterns* (identical wrong answers) have high similarity and are genuinely suspicious. This approach is inherently more resistant to surface-level obfuscation while naturally tolerating stylistic variation.

**Limitation acknowledged:** This method cannot distinguish two students who independently arrived at the same incorrect approach from actual plagiarism. Human review is always required.

---

### 3.3 Contribution 3: Playwright-Based Full Grade Round-Trip Automation for Sakai/eFundi

**Claim:** The system implements the first documented fully automated grade round-trip pipeline for a Sakai LMS instance using headless browser automation (Playwright), encompassing: session persistence, submission ZIP download, assessment, feedback injection, and grade upload — without requiring institutional API access or LMS administrator credentials.

**Technical Significance:** The Sakai REST API is sparsely documented and institution-specific in its availability. Many universities running Sakai do not expose full gradebook write APIs to teaching staff. The Playwright-based approach operates at the HTTP/browser layer, using only lecturer-level credentials and the standard web interface. This dramatically reduces the deployment barrier for automated grading at Sakai institutions.

**Prior art gap:** Playwright-based Sakai automation is not documented in any reviewed academic or commercial grading system.

---

### 3.4 Contribution 4: Three-Agent Orchestration Architecture for Assessment Quality Control

**Claim:** HOMS v3.0 introduces a three-agent architecture (AssessmentAgent + ModerationAgent + LearningAgent) with defined inter-agent contracts and a sequential pipeline orchestrator (WorkflowEngine), as a reusable design pattern for assessment systems.

**Architectural Significance:**
- Most APA systems are monolithic: they assess and output grades in a single pipeline.
- The explicit separation of *grading* (AssessmentAgent), *quality control* (ModerationAgent), and *insight generation* (LearningAgent) enables each concern to be independently configured, replaced, or extended.
- The ModerationAgent introduces automated statistical quality control — applying z-score outlier detection and threshold rules as a post-processing pass — which reduces lecturer time spent on manual review by pre-filtering the cases that genuinely need attention.
- The LearningAgent's accumulation of per-annotation difficulty scores across multiple cohort runs creates a *continuous improvement loop*: assessment insights directly inform which topics need more instructional attention in subsequent semesters.

**Prior art gap:** No reviewed open-source APA system implements an explicit moderation agent with statistical outlier detection as a post-processing pass over bulk assessment results.

---

### 3.5 Contribution 5: AI-Powered Rubric Extraction from Unstructured Documents

**Claim:** The system uses GPT-4 to automatically extract structured, machine-readable rubric criteria from arbitrary DOCX and PDF rubric documents, eliminating the need for lecturers to manually re-encode rubrics in JSON/YAML.

**Technical Significance:** Rubric documents at universities are typically formatted for human reading — free-form tables, narrative descriptions, mixed numbering schemes. Converting these to machine-readable structured formats is a significant barrier to automation adoption. By using GPT-4's document understanding capabilities with a specialised extraction prompt, HOMS v3.0 can ingest rubrics "as-is" from the lecturer's existing documents.

**Prior art gap:** While document AI (e.g., Azure Form Recognizer) can extract table structures, using an LLM specifically for rubric semantic understanding (identifying criterion names, weight values, and grading level descriptions) in an APA context is not documented in the reviewed literature.

---

### 3.6 Contribution 6: In-Document Feedback Annotation (DOCX and PDF)

**Claim:** HOMS v3.0 generates annotated versions of student submission documents — adding inline GPT-generated feedback as DOCX comment runs or PyMuPDF text overlay annotations — so feedback is spatially co-located with the relevant text rather than delivered as a separate document.

**Significance:** Research in educational assessment (Nicol & Macfarlane-Dick, 2006) consistently shows that feedback is most effective when it is specific and located adjacent to the relevant passage. Most automated grading systems deliver feedback as a summary table or appended report. Injecting feedback directly into the student's own document at the paragraph level is a meaningful pedagogical improvement.

**Technical detail:** For DOCX, `python-docx` is used to append highlighted runs and a structured feedback table. For PDF, PyMuPDF `fitz.Page.add_text_annot()` places annotations at computed paragraph boundary coordinates. This produces a submission-returned document where every criterion's comment appears near the relevant text.

---

### 3.7 Contribution 7: Persistent Learning Across Assessment Cohorts

**Claim:** The LearningAgent maintains a persistent knowledge base that accumulates annotation difficulty scores, common error frequencies, and temporal trends across multiple assessment runs, enabling semester-on-semester improvement of curriculum design based on empirical data.

**Significance:** Most APA systems are stateless between runs — they assess a cohort and produce a grade sheet, but do not record longitudinal patterns. The LearningAgent's knowledge base creates an institutional memory of student performance patterns tied to specific rubric criteria and PyBryt annotations. Over several cohorts, this produces actionable recommendations (e.g., "Students consistently fail the 'check_loop_structure' annotation — consider revising the related lecture material") grounded in empirical data rather than lecturer intuition.

**Prior art gap:** Longitudinal learning analytics integrated into the assessment execution engine itself (rather than as a separate analytics platform) is not documented in reviewed APA systems.

---

## 4. Feature-by-Feature Novelty Analysis

| Feature | Novelty Level | Justification |
|---------|---------------|---------------|
| PyBryt reference-based assessment | **Incremental** | PyBryt itself is novel (Microsoft, 2021); HOMS applies it in a structured workflow |
| GPT-4 rubric-based essay grading | **Incremental** | LLM grading is published; HOMS automates the complete rubric-to-feedback pipeline |
| Dual offline+cloud hybrid architecture | **Novel** | Combination not documented in prior APA literature |
| Annotation-vector plagiarism detection | **Novel** | New algorithmic approach distinct from all major reviewed plagiarism detectors |
| Playwright Sakai/eFundi automation | **Novel** | Full grade round-trip via browser automation not documented for Sakai |
| GPT rubric extraction from DOCX/PDF | **Combinatorial** | Combination of LLM + document parsing for rubric extraction is new in APA context |
| In-document DOCX/PDF feedback injection | **Combinatorial** | Spatial co-location of AI feedback in student documents is novel in APA context |
| Three-agent moderation architecture | **Novel architecture** | Explicit moderation agent with statistical QC not found in reviewed APA systems |
| Longitudinal LearningAgent knowledge base | **Novel** | Cross-cohort accumulation within assessment engine is new |
| Statistical z-score moderation | **Incremental** | Statistical outlier detection is established; application as an automated APA post-pass is novel in context |
| eFundi ZIP repackaging | **Applied novelty** | Specific to Sakai ZIP format; novel in APA automation literature |
| Fallback degradation (no PyBryt) | **Good practice** | Not novel, but noteworthy for reliability engineering |
| Git-versioned assessment runs | **Incremental** | Git as audit log for grading is documented but rarely implemented in APA tools |

---

## 5. Comparative Analysis vs. Existing Systems

### 5.1 vs. Gradescope / CodeGrade

| Capability | HOMS v3.0 | Gradescope | CodeGrade |
|------------|-----------|------------|-----------|
| Offline operation | ✅ Full offline | ❌ Cloud-only | ❌ Cloud-only |
| PyBryt reference checking | ✅ | ❌ | ❌ |
| GPT essay assessment | ✅ | ✅ (Gradescope AI) | ❌ |
| Automated eFundi integration | ✅ Playwright | ❌ | ❌ |
| Annotation-vector plagiarism | ✅ | ❌ | ❌ |
| In-document feedback injection | ✅ DOCX + PDF | Partial (PDF) | ❌ |
| Open source | ✅ | ❌ | Partial |
| Statistical moderation agent | ✅ | ❌ | ❌ |
| Cross-cohort learning analytics | ✅ | Limited | ❌ |
| Cost | Free (self-hosted) | Per-submission fee | Per-student fee |

### 5.2 vs. MOSS / JPlag (Plagiarism Only)

| Capability | HOMS v3.0 | MOSS | JPlag |
|------------|-----------|------|-------|
| Plagiarism detection | ✅ Annotation-vector | ✅ Token-based | ✅ Token/AST |
| Resistant to variable renaming | ✅ | ❌ | Partial |
| Integrated with grading pipeline | ✅ | ❌ | ❌ |
| Handles Python notebooks | ✅ | Partial | Limited |

### 5.3 vs. Web-CAT

| Capability | HOMS v3.0 | Web-CAT |
|------------|-----------|---------|
| Code assessment | ✅ PyBryt trace | ✅ Unit tests + coverage |
| Written assignment assessment | ✅ GPT | ❌ |
| LMS integration | ✅ Sakai/eFundi | Partial (older Sakai) |
| Modern web UI | ✅ React | ❌ (legacy JSP) |
| AI feedback generation | ✅ | ❌ |

### 5.4 vs. Turnitin / iThenticate (Plagiarism Only)

| Capability | HOMS v3.0 | Turnitin |
|------------|-----------|---------|
| Plagiarism detection | ✅ Behavioural | ✅ Text-similarity |
| Code-specific detection | ✅ | Limited |
| Integrated with auto-grading | ✅ | ❌ |
| Cost | Free | Per-submission fee |

---

## 6. Limitations on Novelty Claims

### 6.1 Industrial / Commercial Prior Art

The comparison above is limited to publicly documented academic and open-source systems. Commercial EdTech systems (Turnitin Gradescope AI, ETS e-rater, Pearson automated scoring) have unpublished internal architectures that may overlap with some HOMS v3.0 features. The annotation-vector plagiarism claim in particular should be verified against commercial patent databases before asserting primary novelty.

### 6.2 Scope Limitations

HOMS v3.0 is purpose-built for **NWU UTEW221**. While the architecture is extensible, several components (rubric parser regex patterns, eFundi Playwright selectors, `UTEW221Adapter`) are institution- and course-specific. Generalisation to other institutions and LMSes would require significant adaptation effort.

### 6.3 Scale Validation

No published performance benchmarks exist for HOMS v3.0 at scale (>500 students per cohort). The async job architecture and MongoDB persistence are designed for scale, but the PyBryt kernel execution model (one Jupyter kernel per submission) may create bottlenecks at very large cohort sizes.

### 6.4 AI Grading Reliability

The GPT-4 assessment component inherits all known limitations of LLM-based grading:
- Hallucination risk in feedback text.
- Inconsistency across API calls (non-zero temperature).
- Sensitivity to prompt wording.
- Inability to verify factual claims in student writing.

HOMS v3.0 does not include a human-in-the-loop validation step for AI-generated grades, which is a limitation compared to systems like Gradescope that require TA approval before grade release.

### 6.5 Plagiarism Detection False Positive Rate

The annotation-vector similarity approach has not been validated against a labelled dataset of genuine plagiarism cases. The 0.85 default threshold is heuristic. False positive rates for students who independently produce correct solutions could be high on simple assignments with few annotations.

---

## 7. Summary Novelty Matrix

| Dimension | Rating (1–5) | Notes |
|-----------|-------------|-------|
| **Technical novelty** | 3.5/5 | Novel annotation-vector plagiarism; builds on existing PyBryt + GPT-4; not a new algorithm from scratch |
| **Combinatorial novelty** | 4.5/5 | The offline+cloud hybrid + Playwright Sakai + three-agent moderation combination is highly original |
| **Applied novelty** | 5/5 | No reviewed system automates the complete NWU eFundi grade round-trip end-to-end |
| **Architectural novelty** | 4/5 | Three-agent architecture with ModerationAgent is a meaningful design contribution |
| **Pedagogical novelty** | 4/5 | In-document spatial feedback + cross-cohort LearningAgent address documented gaps in APA feedback quality |
| **Accessibility novelty** | 4.5/5 | Offline capability removes cloud API cost barrier for resource-constrained institutions |

**Overall Novelty Assessment: HIGH (4.1/5)**

The system makes a meaningful and original contribution to the field of automated academic assessment, particularly in its hybrid architecture, applied LMS automation, and annotation-vector approach to plagiarism detection. The primary strength of the novelty claim is combinatorial: the integration of PyBryt, GPT-4, Playwright-based Sakai automation, and multi-agent quality control into a single deployable system is not documented elsewhere.

---

## 8. Recommendations for Future Work

### 8.1 Validate Annotation-Vector Plagiarism at Scale

Design a controlled study with labelled plagiarism cases to measure precision, recall, and F1 score of the annotation-vector similarity detector versus MOSS and JPlag on the same dataset.

### 8.2 Human-in-the-Loop Approval Workflow

Add a lecturer approval step before GPT-generated grades are written to eFundi. This addresses the AI grading reliability limitation and aligns with best practices for AI-assisted grading.

### 8.3 Generalise Beyond eFundi

Abstract the eFundi integration behind an `LMSAdapter` interface and implement adapters for Moodle, Blackboard, and Canvas, significantly expanding the system's applicability.

### 8.4 Rubric Reliability Study

Conduct inter-rater reliability studies comparing GPT-4 scores with human TAs on UTEW221 assignments to quantify agreement, calibration, and systematic biases.

### 8.5 Multi-Language Code Assessment

Extend PyBryt-based assessment to languages beyond Python (R, Julia, Java) to support STEM courses beyond computer science.

### 8.6 Explainability Layer

Add an explainability module that translates PyBryt annotation failures into student-friendly natural language explanations tied to specific course learning outcomes.

### 8.7 Publish as Research Artefact

The system should be written up and submitted to a venue such as **ICER** (International Computing Education Research), **EDM** (Educational Data Mining), or **LAK** (Learning Analytics and Knowledge) to formally establish the novelty claims and solicit community feedback.

---

## References

- Douce, C., et al. (2005). Automatic test-based assessment of programming. *Journal on Educational Resources in Computing*, 5(3).
- Ihantola, P., et al. (2010). Review of recent systems for automatic assessment of programming assignments. *Proceedings of the 10th Koli Calling International Conference on Computing Education Research*.
- Microsoft Research. (2021). *PyBryt: Reference implementations for automated feedback*. https://github.com/microsoft/pybryt
- Mizumoto, A., & Eguchi, M. (2023). Exploring the potential of using an AI language model for automated essay scoring. *Research Methods in Applied Linguistics*, 2(2).
- Nicol, D. J., & Macfarlane-Dick, D. (2006). Formative assessment and self-regulated learning: A model and seven principles of good feedback practice. *Studies in Higher Education*, 31(2), 199–218.
- Yan, D., et al. (2024). Practical and ethical challenges of large language models in education: A systematic scoping review. *British Journal of Educational Technology*, 55(1).
- Sakai Project. (2024). *Sakai LMS documentation*. https://www.sakailms.org
- Playwright. (2024). *Playwright for Python documentation*. https://playwright.dev/python
