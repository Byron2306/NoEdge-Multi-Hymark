# Smart Assessor - AI-Powered Assignment Grading System

## Original Problem Statement
Fix and enhance the assessor app to be AI-powered, highly flexible for any assignment type including argumentative essays. Key requirements:
- Parse different rubrics and essay matrices
- Understand assessment criteria
- Download bulk assignment ZIP from eFundi
- Extract and individually parse student submissions (PDF/DOCX)
- AI-powered scoring with GPT
- Annotate quality feedback ON THE DOCUMENT in red text
- Fill out rubrics and save feedback in same folder structure
- Record marks in CSV grades file

**NEW REQUIREMENT (April 2026):** Build an Exam Builder feature to generate complete History exam papers.

## User Personas
1. **University Lecturer/Marker** - Needs to efficiently grade large batches of essays with consistent, fair assessment
2. **Teaching Assistant** - Assists with grading workload, needs clear rubric guidance
3. **Course Administrator** - Manages bulk submissions via eFundi, needs streamlined upload/download
4. **Exam Creator** - Needs to generate high-quality exam papers with legitimate historical sources

## Core Requirements (Static)
- AI-powered essay assessment using GPT-4o
- Rubric parsing (DOCX/PDF) including essay matrices
- Document parsing (DOCX/PDF) with image extraction
- Red-text annotations on original documents
- eFundi ZIP bulk processing
- CSV grade file updates
- Default essay rubric creation
- **Exam Builder for generating 125-mark History papers**

## Architecture
```
Frontend (React)         Backend (FastAPI)          Database (MongoDB)
├── Assess Tab    <-->   /api/assess/*       <-->   assessments_collection
├── Exam Builder  <-->   /api/exams/*        <-->   exams_collection
├── Rubrics Tab   <-->   /api/rubric/*       <-->   rubrics_collection
└── Jobs Tab      <-->   /api/job/*          <-->   jobs_collection
```

## What's Been Implemented

### Exam Builder Feature (April 1, 2026) ✅ NEW
- [x] **Exam generation endpoint** (`POST /api/exams/generate`)
- [x] **Source-based questions** - AI generates legitimate historical sources (speeches, cartoons, photographs, documents)
- [x] **Methodology question** - Lesson planning task for trainee teachers with marking rubric
- [x] **Essay question** - With full essay assessment matrix (5 criteria, 50 marks)
- [x] **DOCX generation** - Professionally formatted exam paper
- [x] **Exam listing** (`GET /api/exams`)
- [x] **Exam download** (`GET /api/exams/download/{filename}`)
- [x] **Frontend UI** - Full form with topic inputs, suggestion chips, validation
- [x] **Recent Exams list** - Shows previously generated exams
- [x] **MongoDB persistence** - Exams stored in `exams` collection

### Backend Features (Original)
- [x] Health check endpoint
- [x] Rubric upload and parsing (DOCX/PDF)
- [x] AI-powered rubric extraction using GPT
- [x] Default essay rubric creation (5 criteria, 50 marks)
- [x] Single submission assessment with AI feedback
- [x] Bulk ZIP assessment for eFundi
- [x] Document annotation with red text
- [x] **CSV grade file updates** - FIXED: Now correctly updates `grade` column
- [x] **Annotated document in correct folder** - FIXED: Feedback placed in `Feedback Attachment(s)/` folder
- [x] **Same filename for annotated docs** - FIXED: Annotated DOCX keeps original filename
- [x] Annotated document download
- [x] Job status tracking for bulk assessments
- [x] **Group member detection** - Extracts student IDs from first page and applies same grade
- [x] **Score validation** - Recalculates total from criteria scores to fix AI math errors
- [x] **Balanced grading prompt** - ~65% average with meaningful variation (36%-80% range)

### Frontend Features
- [x] Four-tab interface (Assess, **Exam Builder**, Rubrics, Jobs)
- [x] File upload dropzones
- [x] Rubric selection cards
- [x] Bulk eFundi ZIP assessment
- [x] Single file assessment
- [x] Toast notifications
- [x] **Download ZIP button** - FIXED: Using fetch+blob for reliable downloads
- [x] **Job Results Modal** - Per-student breakdown with scores, criteria, feedback
- [x] **Expandable student details** - Click to see strengths, improvements, overall feedback
- [x] **Group member badges** - Shows group submissions with member count
- [x] **Stats dashboard** - Shows average, range, pass rate for each job
- [x] **Expandable Rubric Criteria** - Click criteria to see level descriptions and score ranges
- [x] **Live Progress Monitoring** - Real-time progress overlay during bulk assessment

### Backend Features (March 10, 2026)
- [x] **PDF Annotation Support** - Using PyMuPDF for highlights, sticky notes, score box
- [x] **Live Job Progress** - Real-time updates to database during processing
- [x] **Assignment Instructions** - Upload or paste task instructions for AI context
- [x] **Improved DOCX Annotations**:
  - Front page score box with ✓/✗ pass/fail symbol
  - Criteria breakdown with ticks/crosses
  - Inline comments with symbols ([✓ #1], [✗ #2], [→ #3])
  - Short summary feedback
- [x] **Two Feedback Files Per Student**:
  - Annotated submission (score + inline comments)
  - Filled rubric document (criteria table with achieved levels)
- [x] **History-Specific Feedback** - AI prompt includes historical thinking skills

### AI Integration
- [x] GPT-4o for essay assessment
- [x] GPT-4o for exam generation (sources, questions, methodology, essay)
- [x] Criterion-by-criterion scoring
- [x] Strengths and areas for improvement
- [x] Inline annotations with quotes
- [x] AI-powered rubric parsing fallback

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/health | GET | Health check |
| /api/rubric/upload | POST | Upload rubric file |
| /api/rubric/essay-default | POST | Create default essay rubric |
| /api/rubrics | GET | List all rubrics |
| /api/rubric/{id} | GET/DELETE | Get/delete specific rubric |
| /api/assess/single | POST | Assess single submission |
| /api/assess/bulk | POST | Process eFundi ZIP |
| /api/job/{id} | GET | Get job status |
| /api/jobs | GET | List all jobs |
| /api/download/{job_id} | GET | Download results ZIP |
| /api/assessments | GET | List assessments |
| /api/assessment/{id} | GET | Get assessment details |
| /api/assessment/{id}/download | GET | Download annotated document |
| **/api/exams/generate** | **POST** | **Generate new exam paper** |
| **/api/exams** | **GET** | **List all generated exams** |
| **/api/exams/download/{filename}** | **GET** | **Download exam DOCX** |

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- [x] Core AI assessment functionality
- [x] Rubric parsing and management
- [x] Document annotation
- [x] eFundi bulk processing output format
- [x] **Exam Builder feature**

### P1 (High Priority)
- [ ] Fix Essay Matrix rubric parsing bug (user-reported issue)
- [ ] Background task stability (jobs die on server restart)
- [ ] Upload to eFundi functionality

### P2 (Medium Priority)
- [ ] eFundi automation (Playwright - currently broken)
- [ ] OCR support for image-based submissions
- [ ] Plagiarism detection integration
- [ ] Historical grade analytics
- [ ] Rubric editor UI

### P3 (Nice to Have)
- [ ] Multi-language support
- [ ] Voice feedback annotations
- [ ] Integration with other LMS platforms
- [ ] Mobile app

## Next Tasks
1. Fix Essay Matrix rubric parsing for complex table structures
2. Implement Upload to eFundi feature
3. Add background task recovery mechanism
4. Fix eFundi automation (Playwright script)

## Tech Stack
- Frontend: React 18, Tailwind CSS, Lucide Icons
- Backend: FastAPI, Python 3.x
- Database: MongoDB
- AI: OpenAI GPT-4o
- Document Processing: python-docx, PyMuPDF, PyPDF2
