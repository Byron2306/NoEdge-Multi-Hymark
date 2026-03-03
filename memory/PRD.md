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

## User Personas
1. **University Lecturer/Marker** - Needs to efficiently grade large batches of essays with consistent, fair assessment
2. **Teaching Assistant** - Assists with grading workload, needs clear rubric guidance
3. **Course Administrator** - Manages bulk submissions via eFundi, needs streamlined upload/download

## Core Requirements (Static)
- AI-powered essay assessment using GPT-4o
- Rubric parsing (DOCX/PDF) including essay matrices
- Document parsing (DOCX/PDF) with image extraction
- Red-text annotations on original documents
- eFundi ZIP bulk processing
- CSV grade file updates
- Default essay rubric creation

## Architecture
```
Frontend (React)         Backend (FastAPI)          Database (MongoDB)
├── Assess Tab    <-->   /api/assess/*       <-->   assessments_collection
├── Rubrics Tab   <-->   /api/rubric/*       <-->   rubrics_collection
└── Jobs Tab      <-->   /api/job/*          <-->   jobs_collection
```

## What's Been Implemented (March 3, 2026)

### Backend Features
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
- [x] Three-tab interface (Assess, Rubrics, Jobs)
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
- [x] **Rubric criteria viewer** - Shows all criteria with mark allocations

### Frontend Features
- [x] Modern dark-themed UI with responsive design
- [x] File upload dropzones (drag & drop)
- [x] Rubric selection and management
- [x] Assessment details modal with full feedback
- [x] Job status monitoring
- [x] Download results functionality

### AI Integration
- [x] GPT-4o for essay assessment
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

## Prioritized Backlog

### P0 (Critical)
- [x] Core AI assessment functionality
- [x] Rubric parsing and management
- [x] Document annotation
- [x] **FIXED: eFundi bulk processing output format** - Grades in CSV, feedback in correct folders, same filenames

### P1 (High Priority)
- [ ] PDF annotation support (currently only DOCX)
- [ ] Real-time progress updates for bulk jobs
- [ ] Email notifications on job completion
- [ ] Support for multiple rubric formats

### P2 (Medium Priority)
- [ ] Plagiarism detection integration
- [ ] Historical grade analytics
- [ ] Rubric editor UI
- [ ] Student feedback portal

### P3 (Nice to Have)
- [ ] Multi-language support
- [ ] Voice feedback annotations
- [ ] Integration with other LMS platforms
- [ ] Mobile app

## Next Tasks
1. Add PDF annotation support using PyMuPDF
2. Implement webhook callback for eFundi integration
3. Add progress streaming via WebSocket
4. Create rubric template library

## Tech Stack
- Frontend: React 18, Tailwind CSS, Lucide Icons
- Backend: FastAPI, Python 3.x
- Database: MongoDB
- AI: OpenAI GPT-4o
- Document Processing: python-docx, PyPDF2
