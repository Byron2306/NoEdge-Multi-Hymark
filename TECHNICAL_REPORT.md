# Technical Report: NoEdge-Multi-Hymark (HOMS v3.0)

## Hybrid Offline Marking System — Detailed Verbose Technical Report

**System Name:** NoEdge-Multi-Hymark / HOMS v3.0  
**Institution:** North-West University (NWU), South Africa  
**Domain:** UTEW221 (University Teaching, Engineering Writing)  
**Report Date:** March 2026  
**Version:** 3.0.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview and Purpose](#2-system-overview-and-purpose)
3. [Architecture Overview](#3-architecture-overview)
4. [Component Deep-Dive: Local HOMS CLI System](#4-component-deep-dive-local-homs-cli-system)
5. [Component Deep-Dive: Smart Assessor (AI Backend + Frontend)](#5-component-deep-dive-smart-assessor-ai-backend--frontend)
6. [Data Models and Persistence](#6-data-models-and-persistence)
7. [Technology Stack](#7-technology-stack)
8. [Configuration and Deployment](#8-configuration-and-deployment)
9. [Supported File Formats](#9-supported-file-formats)
10. [Assessment Pipelines and Data Flows](#10-assessment-pipelines-and-data-flows)
11. [API Reference](#11-api-reference)
12. [eFundi / LMS Integration](#12-efundi--lms-integration)
13. [Quality Control and Moderation](#13-quality-control-and-moderation)
14. [Reporting and Output Artifacts](#14-reporting-and-output-artifacts)
15. [Testing Infrastructure](#15-testing-infrastructure)
16. [Security and Resource Management](#16-security-and-resource-management)
17. [Known Limitations and Failure Modes](#17-known-limitations-and-failure-modes)
18. [Glossary](#18-glossary)

---

## 1. Executive Summary

**NoEdge-Multi-Hymark** is a dual-mode, AI-augmented academic assessment platform purpose-built for the NWU UTEW221 course. It combines two tightly coupled but independently operable sub-systems:

1. **Local HOMS (Hybrid Offline Marking System)** — a Python-based command-line and lightweight-web batch processing engine that uses *PyBryt* reference implementations and custom rubrics to automatically grade student programming assignments and Jupyter notebooks offline without dependency on cloud services.

2. **Smart Assessor** — a cloud-capable, full-stack web application (FastAPI backend + React frontend) that leverages OpenAI GPT models for natural-language AI assessment of written assignments, provides a rich browser-based user interface for real-time batch job management, and automates the complete grade round-trip with the eFundi (Sakai) Learning Management System via Playwright browser automation.

Together, the system addresses the end-to-end academic assessment lifecycle: ingestion of student submissions (direct upload or eFundi download), automated grading (code trace analysis or AI linguistic evaluation), quality control through a three-agent moderation architecture, structured feedback generation, and result distribution back to the LMS.

---

## 2. System Overview and Purpose

### 2.1 Problem Context

Large undergraduate cohorts at NWU generate hundreds of programming and written assignments per assessment cycle. Manual grading at this scale is labour-intensive, inconsistent, and slow. Traditional auto-graders are narrow and cannot handle rubric-weighted partial credit, plagiarism detection, or natural-language feedback for prose submissions.

### 2.2 Design Goals

| Goal | How Addressed |
|------|---------------|
| Offline-capable grading | Local HOMS runs without internet using PyBryt PKL reference files |
| AI-quality feedback | Smart Assessor uses GPT-4 for rubric-driven textual assessment |
| LMS interoperability | Playwright-based eFundi automation for download and upload |
| Consistency and fairness | ModerationAgent enforces statistical outlier detection and plagiarism checks |
| Scalability | Async bulk processing jobs; React frontend with live progress tracking |
| Extensibility | Three-tier agent architecture; pluggable rubric formats |

### 2.3 Intended Audience / Users

- **Lecturers / Teaching Assistants**: Run batch assessments via CLI or web UI
- **System Administrators**: Configure eFundi session, MongoDB, OpenAI API key
- **Students**: Indirectly — receive annotated feedback documents and grades through eFundi

---

## 3. Architecture Overview

The repository is structured as a monorepo containing three independently runnable code trees alongside shared configuration:

```
NoEdge-Multi-Hymark/
│
├── backend/server.py           ← Smart Assessor: FastAPI REST server (2,578 lines)
│
├── frontend/                   ← Smart Assessor: React SPA (App.js 1,421 lines)
│   ├── src/App.js
│   ├── package.json
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── Marker/                     ← Local HOMS scaffold directory
│   ├── homs/                   ← Core Python package
│   │   ├── core/               ← Three assessment agents + workflow engine
│   │   ├── integrations/       ← eFundi + UTEW221 adapter
│   │   ├── utils/              ← Six utility modules
│   │   └── config/
│   ├── scripts/                ← 12 developer/operational helper scripts
│   ├── main.py                 ← HOMS CLI entry point (Marker-local)
│   └── webapp.py               ← HOMS Flask dev server (Marker-local)
│
├── homs_production/            ← Production copy of HOMS (installer artefact)
│
├── main.py                     ← Root CLI entry point
├── webapp.py                   ← Root Flask web app entry point
├── config.json                 ← Central configuration (all settings)
├── requirements.txt            ← Python dependency list
├── pyproject.toml              ← PEP 517 package metadata (homs v3.0.0)
├── backend_test.py             ← Smart Assessor API integration test suite
└── README.md                   ← Operational quick-start guide
```

### 3.1 Dual-Mode Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         HOMS v3.0                                    │
│                                                                      │
│  ┌────────────────────────────┐   ┌─────────────────────────────┐   │
│  │   Mode 1: Local HOMS CLI   │   │  Mode 2: Smart Assessor Web │   │
│  │                            │   │                             │   │
│  │  main.py / webapp.py       │   │  backend/server.py          │   │
│  │       │                    │   │  (FastAPI + OpenAI + Mongo) │   │
│  │  WorkflowEngine            │   │       │                     │   │
│  │    ├─ AssessmentAgent      │   │  frontend/src/App.js        │   │
│  │    │   └─ PyBryt           │   │  (React + TailwindCSS)      │   │
│  │    ├─ ModerationAgent      │   │                             │   │
│  │    ├─ LearningAgent        │   │  MongoDB persistence        │   │
│  │    └─ WorkflowEngine       │   │  Async job queue            │   │
│  │                            │   │  Playwright eFundi bot      │   │
│  │  Output: HTML/JSON/CSV     │   │  Output: Annotated DOCX/PDF │   │
│  └─────────────┬──────────────┘   └──────────────┬──────────────┘   │
│                │                                  │                  │
│         ┌──────▼──────────────────────────────────▼──────┐          │
│         │              eFundi (Sakai LMS)                 │          │
│         │  Playwright automation: download & upload ZIPs  │          │
│         └───────────────────────────────────────────────-┘          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Deep-Dive: Local HOMS CLI System

### 4.1 Three-Agent Architecture

The core assessment logic is divided into three specialised agents that operate in a defined sequence inside the `WorkflowEngine`.

#### 4.1.1 AssessmentAgent (`homs/core/assessment_agent.py`)

**Responsibility:** Evaluate a student submission against a reference implementation and an optional rubric, producing a scored assessment record.

**Lifecycle:**

1. **Initialisation** — An `AssessmentAgent` instance is created at workflow start. Reference implementations (serialised as `.pkl` files by PyBryt) are loaded into an in-memory dictionary keyed by reference name.

2. **Reference Loading** — `load_reference(name, path)` deserialises a `pybryt.ReferenceImplementation` from a `.pkl` file. Multiple references can be registered simultaneously, enabling multi-assignment workflows.

3. **Rubric Loading** — `load_rubric(path)` accepts JSON, YAML, or DOCX-derived rubrics. The rubric maps criterion names to `{"weight": float, "annotations": [str]}` dicts.

4. **Single Assessment** — `assess_submission(submission_path, ref_name, student_id)`:
   - If `.py` file: convert to `.ipynb` using `nbformat` (adds a single code cell).
   - Run `pybryt.StudentImplementation(path)` to capture a memory trace during execution.
   - Call `reference.check(student_impl)` to evaluate all annotations.
   - Extract per-annotation pass/fail results and aggregate into `basic_score` (0–100).
   - If rubric is loaded, apply per-criterion weighting to derive `rubric_score`.
   - Compute `final_score` as the weighted combination.
   - Wrap results in an `assessment` dict (see Section 6.1).

5. **Batch Assessment** — `batch_assess(submissions_dir, reference_name)` iterates over all supported files in a directory, calling `assess_submission` for each and accumulating results.

6. **Statistics** — `get_statistics()` computes mean, standard deviation, median, min, and max scores across the current batch for downstream moderation.

**Fallback Behaviour:** If PyBryt is not importable (e.g., lightweight deployment), the agent falls back to basic Python execution tests with a zero `basic_score`, allowing rubric-only grading to proceed.

---

#### 4.1.2 ModerationAgent (`homs/core/moderation_agent.py`)

**Responsibility:** Apply quality-control rules to the outputs of the AssessmentAgent, flag anomalies, and detect potential plagiarism.

**Moderation Rules (configurable via `config.json`):**

| Rule | Trigger Condition | Flag Label |
|------|-------------------|------------|
| Low Score | `score < low_score_threshold` (default 40) | `low_score` |
| High Score | `score > high_score_threshold` (default 95) | `high_score` |
| Statistical Outlier | `|z-score| > std_dev_multiplier` (default 2.0) | `statistical_outlier` |
| Partial Understanding | annotation pass rate < 30% | `partial_understanding` |
| Plagiarism Suspect | pairwise similarity > threshold (default 0.85) | `potential_plagiarism` |

**Cohort Statistics:** For each batch, the agent calculates `mean`, `std`, `median`, `min`, and `max` scores. The z-score rule normalises each student's score relative to the cohort before flagging.

**Plagiarism Detection:** `detect_plagiarism(assessments, threshold)` performs pairwise comparison of annotation pass/fail vectors. The similarity metric is the proportion of annotations that share the same pass/fail outcome between two submissions. Pairs exceeding the threshold are returned as `(student_id_a, student_id_b, similarity_score)` tuples.

**Output Per Student:**
```json
{
  "student_id": "12345678",
  "action": "review_required",
  "flags": ["low_score", "statistical_outlier"],
  "recommendations": [
    "Score is below 40 — manual review advised",
    "Score deviates significantly from cohort average"
  ],
  "original_score": 22.5,
  "requires_human_review": true
}
```

---

#### 4.1.3 LearningAgent (`homs/core/learning_agent.py`)

**Responsibility:** Accumulate insight about annotation difficulty and common error patterns across assessment runs, enabling data-driven curriculum feedback.

**Knowledge Base Schema:**
```json
{
  "common_errors": {"annotation_name": frequency},
  "difficulty_patterns": {},
  "annotation_performance": {
    "annotation_name": {
      "pass_rate": 0.72,
      "difficulty_score": 0.28,
      "total_attempts": 120
    }
  },
  "temporal_trends": [{"pos": 1, "avg_score": 64.3}],
  "moderation_patterns": {"low_score": 12, "statistical_outlier": 5}
}
```

**Insight Generation:** `get_insights()` returns:
- `most_difficult_annotations`: Top 5 annotations sorted ascending by pass rate.
- `most_common_errors`: Top 5 annotation failure names by frequency.
- `recommendations`: Actionable teaching suggestions, e.g., "Students struggle with [annotation]; consider revising lecture material on this topic."

**Persistence:** `save_knowledge_base(path)` / `load_knowledge_base(path)` enable the agent to accumulate learning across multiple assessment runs over a semester.

---

### 4.2 WorkflowEngine (`homs/core/workflow_engine.py`)

The `WorkflowEngine` is the top-level orchestrator that executes a complete, deterministic 9-step assessment pipeline. It owns instances of all three agents plus the supporting utility managers.

**Constructor Parameters:**
- `config_path`: Accepts a file path (`str`/`Path`) or a pre-loaded dict.

**Full Workflow Sequence:**

| Step | Action | Module Used |
|------|--------|-------------|
| 1 | Create versioned git branch (`assessment_<timestamp>`) | `GitIntegration` |
| 2 | Load rubric from DOCX/JSON/YAML | `RubricParser`, `UTEW221Adapter` |
| 3 | Batch assess all submissions | `AssessmentAgent` |
| 4 | Moderate assessments; detect plagiarism | `ModerationAgent` |
| 5 | Extract learning insights from cohort data | `LearningAgent` |
| 6 | Generate HTML, JSON, CSV reports | `ReportGenerator` |
| 7 | Repackage eFundi ZIP with grades and feedback | `FeedbackPackager` |
| 8 | Persist workflow data to SQLite + JSON | `DataManager` |
| 9 | Git commit and push results | `GitIntegration` |

**Partial Execution:** `run_assessment_only(submissions_dir, reference_name)` provides a shortcut that executes only steps 3–5, bypassing git, eFundi, and full reporting for rapid development iterations.

**Error Handling:** Each step is wrapped in a try/except block. Failures are logged into `workflow_summary.errors[]` without aborting subsequent steps, ensuring maximum output even under partial failure conditions.

---

### 4.3 Utilities (`homs/utils/`)

#### 4.3.1 RubricParser (`rubric_parser.py`)

Parses rubric definitions from multiple formats into the canonical internal JSON format.

- **DOCX Parsing:** Extracts raw XML from the `.docx` zip container, locates text paragraphs that match the pattern `<number> <description> <n> marks`, and constructs criterion dicts.
- **Assignment-Specific Parser:** `rubric_from_assignment1_docx(path)` applies UTEW Assignment 1 formatting conventions for more accurate extraction.
- **YAML/JSON Pass-Through:** Direct load for machine-readable rubric files.

#### 4.3.2 FeedbackPackager (`feedback_packager.py`)

Handles the complex task of re-injecting graded feedback into an eFundi-format submission ZIP.

- **eFundi ZIP Structure:** The eFundi Sakai LMS exports submissions as a ZIP with a `grades.csv` at the root and per-student folders named `SURNAME, NAME(STUDENT_ID)/`.
- **Grade Injection:** `update_grades_csv(csv_bytes, grades_map)` parses the CSV, injects the new grade column values, and returns modified bytes.
- **Feedback Injection:** Per-student JSON feedback files are placed under `Feedback Attachment(s)/` within each student's folder.
- **Comment Injection:** Optional text comments are written to `comments.txt`.
- **Full Repackage:** `repackage_efundi_zip(download_zip, output_zip, grades_map, feedback_files, comments_map)` performs the complete operation atomically.

#### 4.3.3 DataManager (`data_manager.py`)

Dual-mode persistence layer:
- **SQLite:** `homs.db` stores lightweight workflow metadata (`workflow_id`, `timestamp`, `status`, `data_path`).
- **JSON Files:** Full workflow data is written to `./data/workflow_<ID>.json` for complete auditability.

#### 4.3.4 ReportGenerator (`report_generator.py`)

Produces three output artefacts per workflow run:
1. **`summary_report.html`** — Self-contained HTML dashboard with cohort statistics, charts, and per-student score table.
2. **`detailed_report.json`** — Complete assessment data dump including all annotations, flags, moderation outcomes, and learning insights.
3. **`results.csv`** — Spreadsheet-compatible grade sheet with `student_id`, `final_score`, and flag columns.

#### 4.3.5 GitIntegration (`git_integration.py`)

Optional version-control integration (configurable via `config.git.enabled`):
- Creates an `assessment_<timestamp>` branch before each run.
- Stages, commits, and pushes all output artefacts after completion.
- Ensures complete auditability of all assessment runs as git history.

#### 4.3.6 GroupParser (`group_parser.py`)

Extracts group membership metadata from DOCX submissions:
- Parses member names, student numbers, and group size indicators from document headers.
- Enables group-assignment workflows where multiple students share a submission.

---

### 4.4 UTEW221 Adapter (`homs/integrations/utew221_adapter.py`)

A format-normalisation layer specific to the UTEW221 course rubric format:
- **JSON Input:** Handles nested `criteria` lists with `name`, `weight`, and optional `annotations` fields.
- **CSV Input:** Reads `criterion`, `annotation`, `weight` columns.
- **Output:** Internal canonical rubric format, saved as JSON.

---

### 4.5 CLI Interface (`main.py`)

**Usage:**
```bash
python main.py run <SUBMISSIONS_DIR> <REFERENCE_NAME> \
  --reference-path data/references/reference.pkl \
  --output output \
  --config config.json
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `submissions` | positional | Path to directory containing student submission files |
| `reference_name` | positional | Label for the reference implementation (must match loaded PKL) |
| `--reference-path` | option | Path to serialised PyBryt `.pkl` reference file |
| `--output` | option | Output directory for all reports (default: `./output`) |
| `--config` | option | Path to `config.json` (default: `./config.json`) |

---

### 4.6 Flask Development Server (`webapp.py`)

A lightweight Flask application providing a browser-accessible interface for the Local HOMS system during development.

**Routes:**

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Index dashboard with recent workflow history |
| `/upload_reference` | POST | Upload a `.pkl` reference file |
| `/upload_submission` | POST | Upload a single student submission |
| `/assess_single` | POST | Trigger single-submission assessment |
| `/status` | GET | Live progress streaming (SSE or polling) |
| `/reports` | GET | List all generated reports |
| `/reports/<filename>` | GET | Download a specific report file |

---

## 5. Component Deep-Dive: Smart Assessor (AI Backend + Frontend)

### 5.1 FastAPI Backend (`backend/server.py` — 2,578 lines)

The Smart Assessor backend is a production-grade, fully async FastAPI application integrating OpenAI GPT, MongoDB, and Playwright.

#### 5.1.1 Startup and Lifespan

The server uses FastAPI's `lifespan` context manager for clean startup/shutdown logging. CORS middleware is configured with `allow_origins=["*"]` for maximum development flexibility.

#### 5.1.2 AI Assessment Engine

**Rubric Parsing via GPT:** `ai_parse_rubric(content, filename)` sends document content to GPT-4 with a specialised system prompt instructing the model to extract structured rubric criteria with descriptions, weights, and grading levels. The model response is parsed from JSON.

**Essay Default Rubric:** `POST /api/rubric/essay-default` creates a standard five-criterion essay rubric (Content/Argument, Structure/Organisation, Evidence/Research, Language/Style, Referencing) with full GPT-level and score definitions, providing a zero-configuration starting point.

**AI Assessment (`assess_with_ai`):** For each student submission:
1. Build a detailed system prompt embedding the complete rubric definition.
2. Construct a user message with the extracted document content.
3. Call `openai_client.chat.completions.create()` with GPT-4.
4. Parse the structured JSON response for `criteria_scores` (each criterion gets a `level`, `score`, and `feedback` string).
5. Sum criterion scores to derive `total_score`.

**Document Annotation:** After scoring, the system can produce annotated output documents:
- **DOCX Annotation** (`annotate_docx_with_feedback`): Uses `python-docx` to add highlighted commentary runs and a formatted feedback appendix table at the end of the document.
- **PDF Annotation** (`annotate_pdf_with_feedback`): Uses PyMuPDF (`fitz`) to overlay text annotations at paragraph boundaries within the PDF.

#### 5.1.3 Async Job Queue

Bulk assessments (`POST /api/assess/bulk`) are processed as background jobs using FastAPI's `BackgroundTasks`:
- A job record is inserted into MongoDB `jobs` collection with `status: "processing"`.
- The background task iterates over each submission in the uploaded ZIP.
- Job status is updated to `"completed"` or `"failed"` on completion.
- Clients poll `GET /api/job/{job_id}` for progress and results.

**Job Log Streaming:** `GET /api/job/{job_id}/logs` returns detailed per-step execution logs for debugging and auditing.

#### 5.1.4 eFundi Browser Automation (Playwright)

The backend embeds a full Playwright async browser controller:

- **Authentication:** `POST /api/efundi/authenticate` accepts eFundi credentials, launches a headless Chromium browser, and navigates to the configured eFundi base URL. The session state is persisted to disk so subsequent calls reuse the authenticated session without re-login.

- **Session Status:** `GET /api/efundi/status` returns whether a valid stored session exists.

- **Debug Page Capture:** `POST /api/efundi/debug-page` captures the current browser page content and a screenshot for troubleshooting selector issues.

- **Download and Assess:** `POST /api/efundi/download-and-assess` triggers the full automated pipeline:
  1. Use Playwright to navigate to the eFundi assignment page.
  2. Click the "Download All" control to trigger the ZIP download.
  3. Extract student submission files from the ZIP.
  4. Run AI assessment on each submission.
  5. Package results into a feedback ZIP.
  6. Store job record in MongoDB.

- **Upload Results:** `POST /api/efundi/upload-results/{job_id}` takes a completed job's output ZIP and uses Playwright to automate the eFundi feedback upload flow.

- **Webhook:** `POST /api/webhook/efundi` provides an inbound webhook endpoint for potential event-driven eFundi integrations.

---

### 5.2 React Frontend (`frontend/src/App.js` — 1,421 lines)

A Single Page Application built with React 18 and styled with TailwindCSS.

#### 5.2.1 Major UI Sections

| Section | Description |
|---------|-------------|
| **Dashboard** | Overview panel showing recent job counts, last run status, and system health |
| **Rubric Management** | Upload DOCX/PDF/JSON rubric, view parsed criteria, create rubric manually, load essay default |
| **Single Assessment** | Drag-drop upload of one submission + rubric selection, immediate results display |
| **Bulk Assessment** | Upload ZIP of submissions, real-time per-student progress overlay |
| **Job Management** | Searchable list of all past jobs with status badges; expandable per-student result rows |
| **Results Viewer** | Detailed per-criterion score breakdown with feedback text per student |
| **eFundi Panel** | Credential input, connection test, download trigger, upload trigger, status indicator |
| **Reports** | Embedded viewer for HTML/JSON/CSV report artefacts |

#### 5.2.2 Key React Components

- **`JobResultsModal`** — Full-screen modal for viewing all students in a job; expandable rows per student showing per-criterion scores and textual feedback.
- **`LiveProgressOverlay`** — Floating overlay that appears during bulk assessment, showing a per-student progress list with spinning/check indicators that update as the background job progresses via polling.
- **`Toast`** — Notification system for success/error/info messages.
- **`UploadZone`** — Drag-and-drop file upload area with file-type validation.

#### 5.2.3 API Communication

All API calls use the `axios` library with the base URL pointing to the FastAPI server. Long-running operations return a `job_id` and the frontend enters a polling loop (`setInterval`) calling `GET /api/job/{job_id}` every few seconds until the job reaches a terminal state.

---

## 6. Data Models and Persistence

### 6.1 Assessment Record (Local HOMS)

```json
{
  "student_id": "12345678",
  "timestamp": "2026-01-30T11:50:26Z",
  "status": "success",
  "reference_used": "assignment_1_reference",
  "annotations": {
    "check_variable_exists": {"satisfied": true, "details": null},
    "check_loop_structure": {"satisfied": false, "details": "Expected for-loop pattern not found"}
  },
  "total_annotations": 10,
  "passed_annotations": 7,
  "basic_score": 70.0,
  "rubric_score": 65.5,
  "final_score": 68.2,
  "submission_path": "submissions/12345678_assignment1.py"
}
```

### 6.2 Rubric (Internal Canonical Format)

```json
{
  "Biographical issues (Harvard style)": {
    "weight": 6,
    "annotations": ["check_harvard_format", "check_reference_list"]
  },
  "Critical analysis": {
    "weight": 10,
    "annotations": ["check_argument_structure", "check_evidence_cited"]
  }
}
```

### 6.3 Smart Assessor Pydantic Models

```python
class RubricCriterion(BaseModel):
    name: str
    weight: float
    levels: Dict[str, Dict[str, Any]]  # level_name -> {description, min_score, max_score}

class Rubric(BaseModel):
    name: str
    total_marks: float
    criteria: List[RubricCriterion]

class AssessmentResult(BaseModel):
    student_id: str
    total_score: float
    max_score: float
    percentage: float
    criteria_scores: Dict[str, Dict[str, Any]]  # criterion -> {level, score, feedback}
    feedback: str
    annotations: List[Dict[str, Any]]
```

### 6.4 MongoDB Collections

| Collection | Key Fields | Purpose |
|------------|------------|---------|
| `rubrics` | `_id`, `name`, `total_marks`, `criteria[]` | Persisted rubric definitions |
| `assessments` | `_id`, `student_id`, `job_id`, `total_score`, `criteria_scores` | Individual assessment records |
| `jobs` | `_id`, `status`, `created_at`, `results[]`, `logs[]` | Batch job metadata and results |

### 6.5 SQLite Schema (Local HOMS)

```sql
CREATE TABLE workflows (
    workflow_id TEXT PRIMARY KEY,
    timestamp TEXT,
    status TEXT,
    data_path TEXT
);
```

---

## 7. Technology Stack

### 7.1 Backend / Core (Python)

| Library | Version | Purpose |
|---------|---------|---------|
| Python | ≥ 3.8 | Core language |
| FastAPI | Latest | Async REST API framework |
| Flask | ≥ 2.0.0 | Development web server |
| PyBryt | ≥ 0.7.0 | Reference-based code annotation checking |
| NumPy | ≥ 1.21.0 | Numerical computations, statistics |
| Pandas | ≥ 1.3.0 | CSV handling, data manipulation |
| PyYAML | ≥ 5.4.0 | YAML rubric file parsing |
| nbformat | ≥ 5.0.0 | Jupyter notebook format manipulation |
| nbconvert | ≥ 6.0.0 | Notebook execution and conversion |
| jupyter_client | ≥ 6.0.0 | Jupyter kernel lifecycle management |
| Playwright | ≥ 1.42.0 | Headless browser automation for eFundi |
| PyPDF2 | ≥ 3.0.0 | PDF text extraction |
| python-docx | Latest | DOCX creation, reading, annotation |
| PyMuPDF (fitz) | Latest | Advanced PDF rendering and annotation |
| OpenAI Python SDK | Latest | GPT-4 API integration |
| Pydantic | Latest | Request/response data validation |
| pymongo | Latest | MongoDB driver |
| python-dotenv | Latest | `.env` file loading |
| SQLite3 | stdlib | Local workflow metadata database |

### 7.2 Frontend (JavaScript)

| Library | Version | Purpose |
|---------|---------|---------|
| React | 18.2.0 | UI component framework |
| React-DOM | 18.2.0 | DOM rendering |
| react-scripts | 5.0.1 | Create-React-App build toolchain |
| Axios | 1.6.0 | HTTP client for API calls |
| Lucide-React | 0.263.1 | SVG icon set |
| TailwindCSS | Latest | Utility-first CSS framework |
| PostCSS | Latest | CSS post-processing |

### 7.3 Infrastructure

| Component | Technology |
|-----------|------------|
| Database (cloud) | MongoDB |
| Database (local) | SQLite |
| Browser automation | Chromium via Playwright |
| Package management | pip (Python), npm (Node.js) |
| Package format | PEP 517 / setuptools (`pyproject.toml`) |
| Version control | Git (optional integration built-in) |

---

## 8. Configuration and Deployment

### 8.1 Central Configuration (`config.json`)

```json
{
  "assessment": {
    "timeout_seconds": 1200,
    "max_memory_mb": 512
  },
  "moderation": {
    "low_score_threshold": 40,
    "high_score_threshold": 95,
    "std_dev_multiplier": 2.0,
    "similarity_threshold": 0.85
  },
  "learning": {
    "min_samples_for_learning": 10
  },
  "data": { "data_dir": "./data" },
  "git": { "enabled": false, "repo_path": "." },
  "reporting": { "include_html": true, "include_csv": true },
  "output_dir": "./output",
  "rubric_path": "./Rubric-1.docx",
  "assignment1_doc": "./Individual Assignment 1.docx",
  "efundi": {
    "package": true,
    "base_url": "https://efundi.nwu.ac.za",
    "download_zip": "<path_to_efundi_download.zip>",
    "output_zip": "./output/efundi_upload.zip",
    "feedback_dir": "./output/efundi_feedback",
    "comments_json": "",
    "student_id_map": {}
  }
}
```

### 8.2 Environment Variables (Smart Assessor Backend)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT assessment |
| `MONGO_URL` | MongoDB connection string (default: `mongodb://localhost:27017`) |
| `DB_NAME` | MongoDB database name (default: `smart_assessor`) |

### 8.3 Deployment Steps

**Local HOMS:**
```bash
# 1. Create virtualenv
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers (for eFundi)
playwright install chromium

# 4. Compile PyBryt reference
python scripts/compile_reference.py --notebook reference.ipynb --out data/references/reference.pkl

# 5. Run full workflow
python main.py run submissions/ reference_name \
  --reference-path data/references/reference.pkl
```

**Smart Assessor:**
```bash
# Backend
pip install fastapi uvicorn pymongo openai python-docx PyMuPDF PyPDF2 playwright
uvicorn backend.server:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install && npm start
```

---

## 9. Supported File Formats

| Format | Extension | Handling Method |
|--------|-----------|-----------------|
| Python Script | `.py` | Convert to `.ipynb` → PyBryt trace |
| Jupyter Notebook | `.ipynb` | Direct PyBryt `StudentImplementation` |
| DOCX Document | `.docx` | `python-docx` text extraction + annotation |
| PDF Document | `.pdf` | PyPDF2 / PyMuPDF text extraction + annotation |
| Plain Text | `.txt` | Direct string read |
| JSON Rubric | `.json` | Direct parse |
| YAML Rubric | `.yaml` / `.yml` | PyYAML parse |
| ZIP Archive | `.zip` | Bulk submission container (eFundi format) |
| PKL Reference | `.pkl` | PyBryt serialised reference implementation |

---

## 10. Assessment Pipelines and Data Flows

### 10.1 Local HOMS Complete Workflow

```
CLI Input: python main.py run submissions/ ref_name
    │
    ▼
WorkflowEngine.run_complete_workflow()
    │
    ├─[Step 1] GitIntegration.create_branch("assessment_20260130")
    │
    ├─[Step 2] Load Rubric
    │   └─► RubricParser.rubric_from_docx("Rubric-1.docx")
    │       OR UTEW221Adapter.convert_utew221_to_rubric("rubric.json")
    │
    ├─[Step 3] AssessmentAgent.batch_assess("submissions/", "ref_name")
    │   └─► For each file in submissions/:
    │       ├─ If .py → nbformat.writes(notebook) → temp .ipynb
    │       ├─ pybryt.StudentImplementation(path).check(reference)
    │       ├─ Extract annotations dict + pass/fail counts
    │       ├─ Compute basic_score = (passed / total) * 100
    │       ├─ Apply rubric weighting → rubric_score
    │       └─ Return assessment dict
    │
    ├─[Step 4] ModerationAgent.batch_moderate(assessments)
    │   ├─ calc_cohort_stats(assessments) → {mean, std, median}
    │   ├─ For each assessment: apply threshold + z-score rules
    │   ├─ detect_plagiarism(assessments) → suspicious pairs
    │   └─ Return moderation results list
    │
    ├─[Step 5] LearningAgent.learn_from_assessments(assessments, moderations)
    │   ├─ Update annotation_performance dict
    │   ├─ Increment common_errors counters
    │   └─ get_insights() → recommendations
    │
    ├─[Step 6] ReportGenerator.generate_all_reports(data, output_dir)
    │   ├─ summary_report.html
    │   ├─ detailed_report.json
    │   └─ results.csv
    │
    ├─[Step 7] FeedbackPackager.repackage_efundi_zip() (if config.efundi.package)
    │   ├─ Extract grades_map from assessments
    │   ├─ update_grades_csv(original_csv_bytes, grades_map)
    │   ├─ write_feedback_files(results, feedback_dir)
    │   └─ zip_feedback → efundi_upload.zip
    │
    ├─[Step 8] DataManager.save_workflow_data(workflow_id, data)
    │   ├─ Write JSON → data/workflow_<ID>.json
    │   └─ INSERT INTO workflows (SQLite)
    │
    └─[Step 9] GitIntegration.commit_and_push("Assessment run complete")

Output: output/summary_report.html
        output/detailed_report.json
        output/results.csv
        output/efundi_upload.zip
```

### 10.2 Smart Assessor Single Assessment Pipeline

```
POST /api/assess/single  (multipart: submission_file, rubric_id)
    │
    ├─ Fetch rubric from MongoDB by rubric_id
    ├─ extract_document_content(submission_file) → text
    ├─ assess_with_ai(text, rubric)
    │   ├─ Build GPT system prompt with rubric JSON
    │   ├─ openai_client.chat.completions.create(model="gpt-4", ...)
    │   ├─ Parse JSON response → criteria_scores dict
    │   └─ Sum scores → total_score
    ├─ annotate_docx_with_feedback(file, criteria_scores) [if DOCX]
    │   OR annotate_pdf_with_feedback(file, criteria_scores) [if PDF]
    ├─ Store in assessments_collection (MongoDB)
    └─ Return AssessmentResult JSON

Response: {student_id, total_score, percentage, criteria_scores, feedback, ...}
```

### 10.3 Smart Assessor Bulk Assessment Pipeline

```
POST /api/assess/bulk  (multipart: zip_file, rubric_id)
    │
    ├─ Insert job record: {status: "processing", created_at: now}
    ├─ Return {job_id}  ← immediate response
    │
    └─► BackgroundTask: process_bulk_job(job_id, zip_path, rubric_id)
        │
        ├─ Extract ZIP → temp directory
        ├─ For each file in ZIP:
        │   ├─ extract_document_content(file)
        │   ├─ assess_with_ai(content, rubric)
        │   ├─ annotate output document
        │   ├─ Append to results[]
        │   └─ Update job logs[]
        ├─ Package results into output ZIP
        ├─ Update job: {status: "completed", results: [...]}
        └─ Store all assessments in MongoDB

Client polls GET /api/job/{job_id} every 3s until status != "processing"
```

---

## 11. API Reference

### 11.1 Smart Assessor REST API (FastAPI)

All endpoints are prefixed with `/api`.

#### Health

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/api/health` | Liveness check | `{"status": "ok"}` |

#### Rubric Management

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/rubric/upload` | `file: UploadFile` | `{rubric_id, name, criteria[]}` |
| POST | `/api/rubric/create` | `Rubric` JSON | `{rubric_id}` |
| POST | `/api/rubric/essay-default` | — | `{rubric_id, name, criteria[]}` |
| GET | `/api/rubrics` | — | `[{rubric_id, name, total_marks}]` |
| GET | `/api/rubric/{rubric_id}` | — | Full `Rubric` object |
| DELETE | `/api/rubric/{rubric_id}` | — | `{"deleted": true}` |

#### Assessment

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/assess/single` | `submission_file, rubric_id` | `AssessmentResult` |
| POST | `/api/assess/bulk` | `zip_file, rubric_id` | `{job_id}` |
| GET | `/api/job/{job_id}` | — | `{status, results[], progress}` |
| GET | `/api/job/{job_id}/logs` | — | `{logs[]}` |
| GET | `/api/jobs` | — | `[{job_id, status, created_at}]` |
| GET | `/api/download/{job_id}` | — | ZIP file download |
| GET | `/api/assessments` | — | All assessment summaries |
| GET | `/api/assessment/{assessment_id}` | — | Full assessment detail |
| GET | `/api/assessment/{assessment_id}/download` | — | Annotated document download |

#### eFundi Integration

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/efundi/authenticate` | `{username, password}` | `{session_id}` |
| GET | `/api/efundi/status` | — | `{authenticated: bool}` |
| POST | `/api/efundi/debug-page` | — | `{html, screenshot_b64}` |
| POST | `/api/efundi/download-and-assess` | `{course_id, assignment_id}` | `{job_id}` |
| POST | `/api/efundi/upload-results/{job_id}` | — | `{uploaded: true}` |
| POST | `/api/webhook/efundi` | Event payload | `{received: true}` |

---

## 12. eFundi / LMS Integration

eFundi is the Sakai-based Learning Management System used at NWU (`https://efundi.nwu.ac.za`). The system integrates at two levels:

### 12.1 ZIP-Level Integration (Available in Both Modes)

The `FeedbackPackager` module understands the exact directory structure that eFundi exports when a lecturer downloads all submissions:

```
Assignment Name_1/
├── grades.csv
├── SURNAME, FIRSTNAME(12345678)/
│   ├── Submission Attachment(s)/
│   │   └── student_submission.docx
│   ├── Feedback Attachment(s)/       ← Injected by HOMS
│   │   └── feedback_12345678.json
│   └── comments.txt                  ← Injected by HOMS
└── SURNAME2, FIRSTNAME2(87654321)/
    └── ...
```

After assessment, the system repackages the ZIP in this same format with the `grades.csv` updated and feedback files added. The lecturer uploads this ZIP back to eFundi's "Upload All" function and grades appear immediately for all students.

### 12.2 Playwright Automation (Smart Assessor Backend)

For fully automated operation, the backend embeds Playwright to automate the browser:
1. Navigate to eFundi and authenticate.
2. Find the assignment in the gradebook.
3. Click the download control for the submission ZIP.
4. After assessment, navigate to the feedback upload interface.
5. Upload the packaged feedback ZIP.

Session state is serialised to disk, enabling authenticated sessions to persist across restarts without requiring re-login.

---

## 13. Quality Control and Moderation

The ModerationAgent implements a multi-dimensional quality control framework:

### 13.1 Score Threshold Rules

- **Low Score Flag** (`score < 40`): Triggers `review_required` action with a recommendation for manual review. Intended to catch students who may need additional support.
- **High Score Flag** (`score > 95`): Near-perfect scores are flagged to verify no assessment errors occurred.

### 13.2 Statistical Normalisation

For each batch, a cohort z-score is computed: `z = (student_score - cohort_mean) / cohort_std`. Students with `|z| > 2.0` (configurable via `std_dev_multiplier`) are flagged as statistical outliers regardless of absolute score. This catches anomalies that fixed thresholds cannot detect in cohorts with unusual score distributions.

### 13.3 Annotation Quality Check

Submissions where the PyBryt annotation pass rate is below 30% receive a `partial_understanding` flag, indicating the student has only superficially addressed the assessment criteria.

### 13.4 Plagiarism Detection

Pairwise annotation vectors are compared across all students. If two students share the same pass/fail pattern for more than 85% of annotations (configurable), both receive a `potential_plagiarism` flag with a recommendation for academic integrity review. This is annotation-based (behavioural similarity) rather than text-based (lexical similarity), making it robust to code reformatting and variable renaming.

---

## 14. Reporting and Output Artifacts

| Artefact | Format | Location | Contents |
|----------|--------|----------|---------|
| Summary Report | HTML | `output/summary_report.html` | Cohort statistics, charts, score table, insights |
| Detailed Report | JSON | `output/detailed_report.json` | Complete data: annotations, flags, moderation, learning |
| Grade Sheet | CSV | `output/results.csv` | `student_id`, `final_score`, `flags` columns |
| eFundi Upload Package | ZIP | `output/efundi_upload.zip` | Repackaged submissions with grades and feedback |
| Per-Student Feedback | JSON | `output/efundi_feedback/*.json` | Individual assessment breakdown |
| Annotated Submission | DOCX/PDF | Via `/api/assessment/{id}/download` | Submission with in-document feedback comments |
| Knowledge Base | JSON | `data/knowledge_base.json` | Accumulated learning across runs |
| Workflow History | SQLite | `data/homs.db` | Workflow metadata for all runs |

---

## 15. Testing Infrastructure

### 15.1 Backend API Test Suite (`backend_test.py`)

A standalone Python test runner (`SmartAssessorAPITester` class) that exercises all Smart Assessor API endpoints:
- Health check
- Rubric upload, create, list, get, delete
- Single submission assessment with a synthetic DOCX
- Bulk ZIP assessment
- Job status polling loop
- Report/document download
- eFundi authentication and status

**Usage:** `python backend_test.py`

### 15.2 Script-Level Tests (`Marker/scripts/`)

| Script | Purpose |
|--------|---------|
| `run_demo_assessment.py` | End-to-end HOMS demo with sample data |
| `run_fallback_assessment.py` | Tests fallback path when PyBryt is unavailable |
| `test_utew_adapter.py` | Unit test for UTEW221 rubric format conversion |
| `debug_assess.py` | Single-submission debug utility |
| `pybryt_probe.py` | Probe and report PyBryt version and API capabilities |
| `inspect_pybryt.py` | Deep inspect of a reference `.pkl` file |
| `inspect_studentimpl.py` | Inspect a `StudentImplementation` trace |
| `analyze_pdf_submissions.py` | PDF-specific batch analysis |
| `create_demo_reference.py` | Generates a demo PyBryt reference for testing |
| `convert_rubrics_from_docx.py` | Batch conversion of DOCX rubrics to JSON |

---

## 16. Security and Resource Management

### 16.1 Timeouts

| Context | Default | Config Key |
|---------|---------|------------|
| PyBryt assessment execution | 1200 seconds | `assessment.timeout_seconds` |
| API GET requests | 120 seconds | Hardcoded in test client |
| API POST assessment | 180 seconds | Hardcoded in test client |
| Background bulk jobs | No timeout | Async background task |

### 16.2 Memory Limits

Maximum memory per assessment is controlled via `config.assessment.max_memory_mb` (default: 512 MB). This is enforced at the workflow level to prevent runaway notebook executions from exhausting server memory.

### 16.3 CORS Policy

The FastAPI server is configured with `allow_origins=["*"]` which is suitable for development. Production deployments should restrict this to the known frontend origin.

### 16.4 Credentials Handling

- OpenAI API key and MongoDB URL are loaded from environment variables (via `python-dotenv`), never from `config.json`.
- eFundi session state is serialised to disk as Playwright storage state (includes auth cookies). This file should be protected with appropriate filesystem permissions.
- eFundi credentials submitted via `POST /api/efundi/authenticate` are used in-memory only and not persisted.

---

## 17. Known Limitations and Failure Modes

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| PyBryt dependency | If unavailable, code assessment degrades to zero `basic_score` | Rubric-only fallback path implemented |
| OpenAI API latency | GPT assessment adds 5–30s per submission | Async background jobs; progress polling |
| eFundi UI changes | Playwright selectors may break if eFundi updates its HTML | Debug-page endpoint enables rapid selector diagnosis |
| PDF annotation precision | PyMuPDF annotation positions are approximate | Annotations placed near paragraph boundaries |
| Plagiarism detection accuracy | Annotation-vector similarity may produce false positives for correct solutions | Results are flags only; human review is always required |
| DOCX rubric parsing | Relies on regex patterns; non-standard formatting may fail to parse | Fallback to manual JSON rubric creation |
| Single-threaded Flask | Development server is not production-safe | Use FastAPI/uvicorn for production |
| CORS wildcard | Security risk in production | Should be restricted to frontend origin in production |

---

## 18. Glossary

| Term | Definition |
|------|------------|
| **HOMS** | Hybrid Offline Marking System — the local CLI assessment subsystem |
| **PyBryt** | Microsoft open-source Python library for reference-based code annotation checking |
| **Reference Implementation** | A model solution annotated with `pybryt.Annotation` objects and serialised to `.pkl` |
| **Student Implementation** | PyBryt's execution trace capture of a student's code |
| **Annotation** | A named checkable condition in PyBryt (e.g., "check_variable_exists") |
| **eFundi** | NWU's instance of the Sakai open-source Learning Management System |
| **Rubric** | A structured set of weighted criteria used to evaluate a submission |
| **Moderation** | Automated quality-control pass over assessment results to flag anomalies |
| **Cohort** | All students assessed in a single workflow run |
| **WorkflowEngine** | The orchestrator class that coordinates all agents in sequence |
| **Smart Assessor** | The cloud-capable AI-powered web application subsystem |
| **GPT-4** | OpenAI's large language model used for natural-language assessment |
| **Playwright** | Microsoft open-source framework for headless browser automation |
| **SPA** | Single Page Application (the React frontend architecture) |
| **UTEW221** | NWU course code: University Teaching — English Writing, Level 221 |
