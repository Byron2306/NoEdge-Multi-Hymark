"""
Smart Assessor - AI-Powered Assignment Assessment System
FastAPI Backend with OpenAI GPT Integration
"""

import os
import io
import re
import csv
import json
import zipfile
import tempfile
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Playwright for eFundi automation
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

load_dotenv()

# OpenAI client
from openai import OpenAI

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Document processing imports
try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_COLOR_INDEX
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# MongoDB setup
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "smart_assessor")
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
rubrics_collection = db["rubrics"]
assessments_collection = db["assessments"]
jobs_collection = db["jobs"]

# Directories
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
RUBRICS_DIR = BASE_DIR / "rubrics"

for d in [UPLOAD_DIR, OUTPUT_DIR, RUBRICS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Smart Assessor] Starting up...")
    yield
    print("[Smart Assessor] Shutting down...")


app = FastAPI(title="Smart Assessor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== MODELS =====================

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
    criteria_scores: Dict[str, Dict[str, Any]]
    feedback: str
    annotations: List[Dict[str, Any]]


# ===================== DOCUMENT PARSING =====================

def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from a DOCX file."""
    if not DOCX_AVAILABLE:
        # Fallback: extract from zip XML
        return _extract_docx_text_fallback(file_path)
    
    doc = Document(str(file_path))
    paragraphs = []
    for para in doc.paragraphs:
        paragraphs.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.append(cell.text)
    return "\n".join(paragraphs)


def _extract_docx_text_fallback(file_path: Path) -> str:
    """Fallback XML-based DOCX text extraction."""
    with zipfile.ZipFile(file_path) as z:
        xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
    text = re.sub(r'<w:tab/>', '\t', xml)
    text = re.sub(r'</w:p>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from a PDF file."""
    if not PDF_AVAILABLE:
        return ""
    
    text_parts = []
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def extract_document_content(file_path: Path) -> str:
    """Extract text content from a document (PDF or DOCX)."""
    suffix = file_path.suffix.lower()
    if suffix == '.docx':
        return extract_text_from_docx(file_path)
    elif suffix == '.pdf':
        return extract_text_from_pdf(file_path)
    elif suffix == '.txt':
        return file_path.read_text(encoding='utf-8', errors='ignore')
    else:
        return ""


# ===================== RUBRIC PARSING =====================

async def ai_parse_rubric(text: str, file_name: str) -> Dict[str, Any]:
    """Use AI to parse rubric from text when standard parsing fails."""
    
    system_prompt = """You are an expert at parsing academic rubrics. Extract the rubric structure from the provided text.

You MUST respond with valid JSON in this exact format:
{
    "name": "<rubric name>",
    "total_marks": <number>,
    "criteria": [
        {
            "name": "<criterion name>",
            "weight": <max marks for this criterion>,
            "levels": {
                "Excellent": {"description": "<description>", "min_score": <num>, "max_score": <num>},
                "Good": {"description": "<description>", "min_score": <num>, "max_score": <num>},
                "Satisfactory": {"description": "<description>", "min_score": <num>, "max_score": <num>},
                "Needs Improvement": {"description": "<description>", "min_score": <num>, "max_score": <num>}
            }
        }
    ]
}

For essay rubrics, common criteria include:
- Thesis Statement & Argument
- Evidence & Historical Accuracy  
- Analysis & Interpretation
- Structure & Organization
- Language, Style & Referencing

If specific level descriptions aren't provided, create appropriate ones based on the criterion."""

    user_prompt = f"""Parse this rubric document and extract all criteria with their weights and performance levels:

Filename: {file_name}

Content:
{text[:8000]}

Extract all assessment criteria, their weights/marks, and create appropriate performance level descriptions."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"[AI Rubric Parse Error] {e}")
        return None


def parse_essay_matrix_from_docx(file_path: Path) -> Dict[str, Any]:
    """Parse an essay assessment matrix/rubric from a DOCX file."""
    if not DOCX_AVAILABLE:
        return parse_rubric_from_text(extract_document_content(file_path))
    
    doc = Document(str(file_path))
    rubric_data = {
        "name": file_path.stem,
        "total_marks": 0,
        "criteria": []
    }
    
    # Try to extract from tables (typical rubric format)
    for table in doc.tables:
        if len(table.rows) < 2:
            continue
        
        # Get headers (performance levels)
        header_row = table.rows[0]
        levels = []
        for i, cell in enumerate(header_row.cells):
            cell_text = cell.text.strip()
            if i > 0 and cell_text:  # Skip first column (criteria names)
                levels.append(cell_text)
        
        # Parse each criterion row
        for row in table.rows[1:]:
            if len(row.cells) < 2:
                continue
            
            criterion_name = row.cells[0].text.strip()
            if not criterion_name:
                continue
            
            # Extract marks from criterion name if present (e.g., "Thesis [10 marks]")
            marks_match = re.search(r'\[?\(?\s*(\d+)\s*(?:marks?|pts?|points?)?\s*\)?\]?', criterion_name, re.I)
            weight = float(marks_match.group(1)) if marks_match else 10.0
            criterion_name = re.sub(r'\s*\[?\(?\s*\d+\s*(?:marks?|pts?|points?)?\s*\)?\]?\s*$', '', criterion_name, flags=re.I).strip()
            
            criterion = {
                "name": criterion_name,
                "weight": weight,
                "levels": {}
            }
            
            for i, cell in enumerate(row.cells[1:]):
                if i < len(levels):
                    level_name = levels[i]
                    description = cell.text.strip()
                    
                    # Extract score range from level name or description
                    score_match = re.search(r'(\d+(?:\.\d+)?)\s*[-–to]\s*(\d+(?:\.\d+)?)', level_name)
                    if score_match:
                        min_score = float(score_match.group(1))
                        max_score = float(score_match.group(2))
                    else:
                        # Default scoring based on level position
                        total_levels = len(levels)
                        min_score = (total_levels - i - 1) / total_levels * weight
                        max_score = (total_levels - i) / total_levels * weight
                    
                    criterion["levels"][level_name] = {
                        "description": description,
                        "min_score": min_score,
                        "max_score": max_score
                    }
            
            if criterion["levels"]:
                rubric_data["criteria"].append(criterion)
                rubric_data["total_marks"] += weight
    
    # If no tables found, try text-based extraction first
    if not rubric_data["criteria"]:
        text_rubric = parse_rubric_from_text(extract_document_content(file_path))
        if text_rubric["criteria"]:
            return text_rubric
        
        # Last resort: use AI to parse
        text = extract_document_content(file_path)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ai_rubric = loop.run_until_complete(ai_parse_rubric(text, file_path.name))
        loop.close()
        
        if ai_rubric and ai_rubric.get("criteria"):
            return ai_rubric
    
    return rubric_data


def parse_rubric_from_text(text: str) -> Dict[str, Any]:
    """Parse rubric from plain text."""
    rubric_data = {
        "name": "Extracted Rubric",
        "total_marks": 0,
        "criteria": []
    }
    
    lines = text.strip().split('\n')
    
    # Look for criteria patterns
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Pattern: "Criterion Name [X marks]" or "Criterion Name (X)"
        match = re.match(r'^(.+?)\s*[\[\(]?\s*(\d+)\s*(?:marks?|pts?|points?)?\s*[\]\)]?\s*$', line, re.I)
        if match:
            name = match.group(1).strip()
            weight = float(match.group(2))
            
            criterion = {
                "name": name,
                "weight": weight,
                "levels": {
                    "Excellent": {"description": "Outstanding performance", "min_score": weight * 0.8, "max_score": weight},
                    "Good": {"description": "Above average performance", "min_score": weight * 0.6, "max_score": weight * 0.79},
                    "Satisfactory": {"description": "Meets basic requirements", "min_score": weight * 0.4, "max_score": weight * 0.59},
                    "Needs Improvement": {"description": "Below expectations", "min_score": 0, "max_score": weight * 0.39}
                }
            }
            rubric_data["criteria"].append(criterion)
            rubric_data["total_marks"] += weight
    
    return rubric_data


# ===================== AI ASSESSMENT =====================

async def assess_with_ai(
    submission_text: str,
    rubric: Dict[str, Any],
    assignment_instructions: str = ""
) -> Dict[str, Any]:
    """Use GPT to assess a submission against a rubric."""
    
    # Build rubric description for the prompt
    rubric_description = f"Total Marks: {rubric.get('total_marks', 100)}\n\nCriteria:\n"
    for criterion in rubric.get("criteria", []):
        rubric_description += f"\n### {criterion['name']} (Weight: {criterion['weight']} marks)\n"
        for level_name, level_data in criterion.get("levels", {}).items():
            desc = level_data.get("description", "")
            min_s = level_data.get("min_score", 0)
            max_s = level_data.get("max_score", 0)
            rubric_description += f"  - {level_name} ({min_s}-{max_s}): {desc}\n"
    
    # Add assignment context if available
    assignment_context = rubric.get("assignment_context", "")
    submission_requirements = rubric.get("submission_requirements", "")
    
    system_prompt = """You are an expert academic assessor specializing in education methodology and History pedagogy. Your task is to thoroughly evaluate student submissions against the provided rubric.

For each criterion in the rubric:
1. Identify the most appropriate performance level based on the submission
2. Assign a specific score within that level's range
3. Provide specific, constructive feedback with inline quotes from the submission

When assessing lesson plan critiques and improvements, look for:
- Identification of specific flaws in the original AI-generated lesson plan
- Clear explanation of WHY each flaw is problematic
- Practical, actionable improvements
- Attention to handling controversial/sensitive content in diverse classrooms
- Progression from lower to higher order thinking in activities
- Appropriate assessment alignment
- Quality of the improved lesson plan template
- Thoughtful reflection on changes made

You MUST respond with valid JSON in this exact format:
{
    "total_score": <number>,
    "criteria_scores": {
        "<criterion_name>": {
            "level": "<level_name>",
            "score": <number>,
            "feedback": "<detailed feedback with specific examples>",
            "quotes": ["<relevant quote from submission>", ...]
        }
    },
    "overall_feedback": "<comprehensive summary feedback>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "areas_for_improvement": ["<area 1>", "<area 2>"],
    "annotations": [
        {
            "quote": "<exact text from submission>",
            "comment": "<feedback comment>",
            "type": "<praise|suggestion|correction|question>"
        }
    ]
}"""

    context_section = ""
    if assignment_context:
        context_section += f"\n## ASSIGNMENT CONTEXT\n{assignment_context}\n"
    if submission_requirements:
        context_section += f"\n## SUBMISSION REQUIREMENTS\n{submission_requirements}\n"
    if assignment_instructions:
        context_section += f"\n## ADDITIONAL INSTRUCTIONS\n{assignment_instructions}\n"

    user_prompt = f"""Please assess the following student submission against the rubric provided.

## RUBRIC
{rubric_description}
{context_section}

## STUDENT SUBMISSION
{submission_text[:15000]}  

Provide a thorough assessment with specific feedback for each criterion. Include at least 3-5 annotations pointing to specific parts of the text. Be fair but rigorous in your assessment."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"[AI Assessment Error] {e}")
        return {
            "error": str(e),
            "total_score": 0,
            "criteria_scores": {},
            "overall_feedback": "Assessment failed due to an error.",
            "annotations": []
        }


# ===================== DOCUMENT ANNOTATION =====================

def annotate_docx_with_feedback(
    original_path: Path,
    output_path: Path,
    annotations: List[Dict[str, Any]],
    overall_feedback: str
) -> bool:
    """Add red-text annotations to a DOCX document."""
    if not DOCX_AVAILABLE:
        return False
    
    try:
        doc = Document(str(original_path))
        
        # Add feedback header at the beginning
        feedback_para = doc.paragraphs[0].insert_paragraph_before("")
        feedback_run = feedback_para.add_run("=== ASSESSMENT FEEDBACK ===\n\n")
        feedback_run.font.color.rgb = RGBColor(255, 0, 0)
        feedback_run.font.bold = True
        feedback_run.font.size = Pt(12)
        
        overall_run = feedback_para.add_run(f"{overall_feedback}\n\n")
        overall_run.font.color.rgb = RGBColor(255, 0, 0)
        overall_run.font.size = Pt(11)
        
        separator = feedback_para.add_run("=" * 50 + "\n\n")
        separator.font.color.rgb = RGBColor(255, 0, 0)
        
        # Track annotations added
        annotation_map = {}
        for i, ann in enumerate(annotations):
            quote = ann.get("quote", "")
            comment = ann.get("comment", "")
            ann_type = ann.get("type", "suggestion")
            if quote:
                annotation_map[quote.lower().strip()[:50]] = {
                    "number": i + 1,
                    "comment": comment,
                    "type": ann_type
                }
        
        # Process paragraphs and add inline annotations
        for para in doc.paragraphs:
            para_text = para.text.lower()
            for key, ann_data in annotation_map.items():
                if key in para_text:
                    # Add annotation after the paragraph
                    ann_run = para.add_run(f" [*{ann_data['number']}]")
                    ann_run.font.color.rgb = RGBColor(255, 0, 0)
                    ann_run.font.bold = True
                    ann_run.font.size = Pt(9)
        
        # Add annotation list at the end
        doc.add_paragraph("")
        end_para = doc.add_paragraph()
        end_header = end_para.add_run("\n\n=== DETAILED ANNOTATIONS ===\n\n")
        end_header.font.color.rgb = RGBColor(255, 0, 0)
        end_header.font.bold = True
        
        for i, ann in enumerate(annotations):
            ann_para = doc.add_paragraph()
            ann_num = ann_para.add_run(f"[{i+1}] ")
            ann_num.font.color.rgb = RGBColor(255, 0, 0)
            ann_num.font.bold = True
            
            ann_type = ann.get("type", "suggestion").upper()
            type_run = ann_para.add_run(f"({ann_type}) ")
            type_run.font.color.rgb = RGBColor(180, 0, 0)
            type_run.font.italic = True
            
            comment_run = ann_para.add_run(ann.get("comment", ""))
            comment_run.font.color.rgb = RGBColor(255, 0, 0)
            
            if ann.get("quote"):
                quote_run = ann_para.add_run(f'\n   Re: "{ann["quote"][:100]}..."')
                quote_run.font.color.rgb = RGBColor(150, 0, 0)
                quote_run.font.italic = True
                quote_run.font.size = Pt(9)
        
        doc.save(str(output_path))
        return True
        
    except Exception as e:
        print(f"[Annotation Error] {e}")
        return False


def create_feedback_txt(output_path: Path, assessment: Dict[str, Any]) -> bool:
    """Create a text feedback file as fallback."""
    try:
        content = []
        content.append("=" * 60)
        content.append("ASSESSMENT FEEDBACK")
        content.append("=" * 60)
        content.append("")
        content.append(f"Total Score: {assessment.get('total_score', 0)}")
        content.append("")
        content.append("OVERALL FEEDBACK:")
        content.append(assessment.get("overall_feedback", ""))
        content.append("")
        content.append("STRENGTHS:")
        for s in assessment.get("strengths", []):
            content.append(f"  + {s}")
        content.append("")
        content.append("AREAS FOR IMPROVEMENT:")
        for a in assessment.get("areas_for_improvement", []):
            content.append(f"  - {a}")
        content.append("")
        content.append("DETAILED CRITERIA SCORES:")
        for crit_name, crit_data in assessment.get("criteria_scores", {}).items():
            content.append(f"\n  {crit_name}:")
            content.append(f"    Level: {crit_data.get('level', 'N/A')}")
            content.append(f"    Score: {crit_data.get('score', 0)}")
            content.append(f"    Feedback: {crit_data.get('feedback', '')}")
        content.append("")
        content.append("ANNOTATIONS:")
        for i, ann in enumerate(assessment.get("annotations", [])):
            content.append(f"\n  [{i+1}] ({ann.get('type', 'note').upper()})")
            content.append(f"      {ann.get('comment', '')}")
            if ann.get('quote'):
                content.append(f"      Re: \"{ann['quote'][:100]}...\"")
        
        output_path.write_text("\n".join(content), encoding='utf-8')
        return True
    except Exception as e:
        print(f"[Feedback TXT Error] {e}")
        return False


# ===================== EFUNDI ZIP HANDLING =====================

def extract_student_id(folder_name: str) -> Optional[str]:
    """Extract student ID from folder name like 'SURNAME, NAME(12345678)'."""
    match = re.search(r'\((\d{5,})\)', folder_name)
    return match.group(1) if match else None


def process_efundi_zip(
    zip_path: Path,
    rubric: Dict[str, Any],
    output_dir: Path
) -> Dict[str, Any]:
    """Process an eFundi assignment zip file and assess all submissions."""
    
    results = {
        "job_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "submissions_processed": 0,
        "assessments": [],
        "grades_csv_path": None,
        "output_zip_path": None
    }
    
    temp_dir = Path(tempfile.mkdtemp(prefix="efundi_"))
    
    try:
        # Extract zip
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_dir)
        
        # Find root folder
        contents = list(temp_dir.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            root_dir = contents[0]
        else:
            root_dir = temp_dir
        
        # Find grades.csv
        grades_csv = None
        for f in root_dir.glob("*.csv"):
            if "grade" in f.name.lower():
                grades_csv = f
                break
        
        # Process each student folder
        grades_map = {}
        feedback_files = {}
        comments_map = {}
        
        for student_folder in root_dir.iterdir():
            if not student_folder.is_dir():
                continue
            
            student_id = extract_student_id(student_folder.name)
            if not student_id:
                continue
            
            # Find submission files
            submission_dir = student_folder / "Submission attachment(s)"
            if not submission_dir.exists():
                submission_dir = student_folder
            
            submission_files = list(submission_dir.glob("*.docx")) + \
                              list(submission_dir.glob("*.pdf")) + \
                              list(submission_dir.glob("*.doc"))
            
            if not submission_files:
                continue
            
            # Process first valid submission
            submission_file = submission_files[0]
            submission_text = extract_document_content(submission_file)
            
            if not submission_text.strip():
                continue
            
            # Run AI assessment (synchronously for now)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            assessment = loop.run_until_complete(
                assess_with_ai(submission_text, rubric)
            )
            loop.close()
            
            assessment["student_id"] = student_id
            assessment["student_folder"] = student_folder.name
            assessment["submission_file"] = submission_file.name
            
            # Calculate percentage and final grade
            total_possible = rubric.get("total_marks", 100)
            total_score = assessment.get("total_score", 0)
            percentage = (total_score / total_possible * 100) if total_possible > 0 else 0
            assessment["percentage"] = round(percentage, 2)
            
            # Store grade
            grades_map[student_id] = total_score
            
            # Create annotated feedback document
            feedback_folder = output_dir / "feedback" / student_folder.name / "Feedback Attachment(s)"
            feedback_folder.mkdir(parents=True, exist_ok=True)
            
            # Annotate the original document
            if submission_file.suffix.lower() == '.docx':
                annotated_path = feedback_folder / f"{submission_file.stem}_GRADED.docx"
                annotate_docx_with_feedback(
                    submission_file,
                    annotated_path,
                    assessment.get("annotations", []),
                    assessment.get("overall_feedback", "")
                )
                feedback_files[student_folder.name] = [annotated_path]
            
            # Also create text feedback
            feedback_txt_path = feedback_folder / "feedback.txt"
            create_feedback_txt(feedback_txt_path, assessment)
            if student_folder.name not in feedback_files:
                feedback_files[student_folder.name] = []
            feedback_files[student_folder.name].append(feedback_txt_path)
            
            # Create comments.txt
            comments_map[student_id] = f"Score: {total_score}/{total_possible} ({percentage:.1f}%)\n\n{assessment.get('overall_feedback', '')}"
            
            results["assessments"].append(assessment)
            results["submissions_processed"] += 1
        
        # Update grades.csv
        if grades_csv and grades_csv.exists():
            updated_csv = update_grades_csv(grades_csv, grades_map)
            output_grades = output_dir / "grades.csv"
            output_grades.write_bytes(updated_csv)
            results["grades_csv_path"] = str(output_grades)
        
        # Create output zip for eFundi upload
        output_zip = output_dir / f"efundi_upload_{results['job_id']}.zip"
        repackage_efundi_zip(
            zip_path,
            output_zip,
            grades_map,
            feedback_files,
            comments_map
        )
        results["output_zip_path"] = str(output_zip)
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return results


def update_grades_csv(csv_path: Path, grades_map: Dict[str, Any]) -> bytes:
    """Update grades.csv with assessment scores."""
    csv_bytes = csv_path.read_bytes()
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    
    if len(lines) < 3:
        return csv_bytes
    
    prefix = lines[:2]
    header = lines[2]
    data_lines = lines[3:]
    
    reader = csv.DictReader([header] + data_lines)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=reader.fieldnames, lineterminator="\r\n")
    writer.writeheader()
    
    for row in reader:
        sid = (row.get("ID") or row.get("Display ID") or "").strip()
        if sid in grades_map:
            row["grade"] = str(grades_map[sid])
        writer.writerow(row)
    
    updated = "\r\n".join(prefix) + "\r\n" + out.getvalue().rstrip("\r\n") + "\r\n"
    return updated.encode("utf-8-sig")


def repackage_efundi_zip(
    download_zip: Path,
    output_zip: Path,
    grades_map: Dict[str, Any],
    feedback_files: Dict[str, List[Path]],
    comments_map: Dict[str, str]
) -> Path:
    """Repackage eFundi zip with grades and feedback."""
    
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(download_zip, 'r') as zin, \
         zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        
        names = zin.namelist()
        root = names[0].split('/')[0] if names else ""
        
        for name in names:
            data = zin.read(name)
            
            # Update grades.csv
            if name.endswith("/grades.csv") or name == "grades.csv":
                csv_bytes = data
                text = csv_bytes.decode("utf-8-sig", errors="replace")
                lines = text.splitlines()
                
                if len(lines) >= 3:
                    prefix = lines[:2]
                    header = lines[2]
                    data_lines = lines[3:]
                    
                    reader = csv.DictReader([header] + data_lines)
                    out_io = io.StringIO()
                    writer = csv.DictWriter(out_io, fieldnames=reader.fieldnames, lineterminator="\r\n")
                    writer.writeheader()
                    
                    for row in reader:
                        sid = (row.get("ID") or row.get("Display ID") or "").strip()
                        if sid in grades_map:
                            row["grade"] = str(grades_map[sid])
                        writer.writerow(row)
                    
                    updated = "\r\n".join(prefix) + "\r\n" + out_io.getvalue().rstrip("\r\n") + "\r\n"
                    data = updated.encode("utf-8-sig")
                
                zout.writestr(name, data)
                continue
            
            # Skip comments.txt if we have new ones
            if name.endswith("/comments.txt"):
                folder = name.rsplit("/", 1)[0]
                student_folder = folder.split("/")[-1]
                sid = extract_student_id(student_folder)
                if sid and sid in comments_map:
                    continue
            
            zout.writestr(name, data)
        
        # Add feedback files
        for student_folder, files in feedback_files.items():
            sid = extract_student_id(student_folder)
            if not sid:
                continue
            
            base = f"{root}/{student_folder}"
            fb_dir = f"{base}/Feedback Attachment(s)"
            zout.writestr(fb_dir + "/", b"")
            
            for f in files:
                if f.exists():
                    zout.write(f, arcname=f"{fb_dir}/{f.name}")
        
        # Add comments.txt
        for sid, comment in comments_map.items():
            student_folder = None
            for name in names:
                if name.startswith(root + "/"):
                    parts = name[len(root) + 1:].split("/")
                    if parts and parts[0]:
                        if extract_student_id(parts[0]) == sid:
                            student_folder = parts[0]
                            break
            
            if student_folder:
                path = f"{root}/{student_folder}/comments.txt"
                zout.writestr(path, comment)
    
    return output_zip


# ===================== API ENDPOINTS =====================

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/rubric/upload")
async def upload_rubric(
    file: UploadFile = File(...),
    name: str = Form(None)
):
    """Upload and parse a rubric file (DOCX or PDF)."""
    
    # Validate file type
    allowed_extensions = {'.docx', '.pdf', '.doc', '.txt'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Save file
    file_path = RUBRICS_DIR / file.filename
    try:
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Parse rubric
    try:
        rubric_data = parse_essay_matrix_from_docx(file_path)
    except Exception as e:
        # Clean up failed file
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse rubric file: {str(e)}. Please ensure it's a valid document.")
    
    rubric_data["name"] = name or file.filename
    rubric_data["file_path"] = str(file_path)
    rubric_data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    # Store in MongoDB
    result = rubrics_collection.insert_one(rubric_data)
    rubric_data["_id"] = str(result.inserted_id)
    
    return {
        "success": True,
        "rubric": rubric_data
    }


@app.post("/api/rubric/create")
async def create_rubric(rubric_data: dict):
    """Create a rubric manually with specified criteria."""
    rubric_data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    # Calculate total marks
    total = sum(c.get("weight", 0) for c in rubric_data.get("criteria", []))
    rubric_data["total_marks"] = total
    
    result = rubrics_collection.insert_one(rubric_data)
    rubric_data["_id"] = str(result.inserted_id)
    
    return {
        "success": True,
        "rubric": rubric_data
    }


@app.post("/api/rubric/essay-default")
async def create_default_essay_rubric(
    name: str = Form("Essay Assessment Rubric"),
    total_marks: float = Form(50)
):
    """Create a default essay assessment rubric with standard criteria."""
    
    # Standard essay rubric criteria
    criteria = [
        {
            "name": "Thesis Statement & Argument",
            "weight": total_marks * 0.2,  # 20%
            "levels": {
                "Excellent (80-100%)": {
                    "description": "Clear, focused, arguable thesis directly addressing the prompt. Consistently supports thesis with insightful analysis. Logical, well-structured, persuasive argument.",
                    "min_score": total_marks * 0.2 * 0.8,
                    "max_score": total_marks * 0.2
                },
                "Good (60-79%)": {
                    "description": "Clear thesis addressing the prompt. Generally supports thesis with relevant evidence and analysis. Mostly logical argument.",
                    "min_score": total_marks * 0.2 * 0.6,
                    "max_score": total_marks * 0.2 * 0.79
                },
                "Satisfactory (40-59%)": {
                    "description": "Thesis present but may be vague or underdeveloped. Support limited or superficial. Argument may lack clarity.",
                    "min_score": total_marks * 0.2 * 0.4,
                    "max_score": total_marks * 0.2 * 0.59
                },
                "Needs Improvement (0-39%)": {
                    "description": "Thesis absent, unclear, or doesn't address prompt. Lacks central argument or supporting evidence. Disorganized.",
                    "min_score": 0,
                    "max_score": total_marks * 0.2 * 0.39
                }
            }
        },
        {
            "name": "Evidence & Historical Accuracy",
            "weight": total_marks * 0.3,  # 30%
            "levels": {
                "Excellent (80-100%)": {
                    "description": "Extensive use of accurate, relevant evidence. Evidence integrated seamlessly. Deep understanding demonstrated.",
                    "min_score": total_marks * 0.3 * 0.8,
                    "max_score": total_marks * 0.3
                },
                "Good (60-79%)": {
                    "description": "Good range of accurate evidence. Generally well-integrated. Solid understanding of the period.",
                    "min_score": total_marks * 0.3 * 0.6,
                    "max_score": total_marks * 0.3 * 0.79
                },
                "Satisfactory (40-59%)": {
                    "description": "Some evidence but limited in scope or accuracy. May be listed rather than integrated. Basic understanding.",
                    "min_score": total_marks * 0.3 * 0.4,
                    "max_score": total_marks * 0.3 * 0.59
                },
                "Needs Improvement (0-39%)": {
                    "description": "Little to no relevant evidence. Claims unsubstantiated. Fundamental lack of understanding.",
                    "min_score": 0,
                    "max_score": total_marks * 0.3 * 0.39
                }
            }
        },
        {
            "name": "Analysis & Interpretation",
            "weight": total_marks * 0.3,  # 30%
            "levels": {
                "Excellent (80-100%)": {
                    "description": "Critical thinking and insightful interpretation. Explains how and why events occurred. Identifies nuances and complexities.",
                    "min_score": total_marks * 0.3 * 0.8,
                    "max_score": total_marks * 0.3
                },
                "Good (60-79%)": {
                    "description": "Good analytical skills. Explains key events and significance. Connects cause and effect reasonably well.",
                    "min_score": total_marks * 0.3 * 0.6,
                    "max_score": total_marks * 0.3 * 0.79
                },
                "Satisfactory (40-59%)": {
                    "description": "Basic explanation but analysis often descriptive. Cause-effect may be simplistic or unclear.",
                    "min_score": total_marks * 0.3 * 0.4,
                    "max_score": total_marks * 0.3 * 0.59
                },
                "Needs Improvement (0-39%)": {
                    "description": "Lacks analytical depth. Primarily descriptive. Fails to engage with complexities.",
                    "min_score": 0,
                    "max_score": total_marks * 0.3 * 0.39
                }
            }
        },
        {
            "name": "Structure & Organization",
            "weight": total_marks * 0.1,  # 10%
            "levels": {
                "Excellent (80-100%)": {
                    "description": "Logically structured with clear intro, body, conclusion. Smooth transitions. Each paragraph focused and contributing.",
                    "min_score": total_marks * 0.1 * 0.8,
                    "max_score": total_marks * 0.1
                },
                "Good (60-79%)": {
                    "description": "Recognizable structure. Paragraphs generally organized. Transitions mostly clear.",
                    "min_score": total_marks * 0.1 * 0.6,
                    "max_score": total_marks * 0.1 * 0.79
                },
                "Satisfactory (40-59%)": {
                    "description": "Structure present but inconsistent. Paragraphs may lack focus. Transitions abrupt or missing.",
                    "min_score": total_marks * 0.1 * 0.4,
                    "max_score": total_marks * 0.1 * 0.59
                },
                "Needs Improvement (0-39%)": {
                    "description": "Disorganized. Lacks clear structure. Difficult to follow.",
                    "min_score": 0,
                    "max_score": total_marks * 0.1 * 0.39
                }
            }
        },
        {
            "name": "Language, Style & Referencing",
            "weight": total_marks * 0.1,  # 10%
            "levels": {
                "Excellent (80-100%)": {
                    "description": "Clear, concise, sophisticated writing. Precise vocabulary. Minimal errors. Accurate referencing if required.",
                    "min_score": total_marks * 0.1 * 0.8,
                    "max_score": total_marks * 0.1
                },
                "Good (60-79%)": {
                    "description": "Generally clear and appropriate. Minor errors that don't impede understanding. Mostly accurate referencing.",
                    "min_score": total_marks * 0.1 * 0.6,
                    "max_score": total_marks * 0.1 * 0.79
                },
                "Satisfactory (40-59%)": {
                    "description": "May be unclear or contain frequent errors. Inconsistent referencing.",
                    "min_score": total_marks * 0.1 * 0.4,
                    "max_score": total_marks * 0.1 * 0.59
                },
                "Needs Improvement (0-39%)": {
                    "description": "Unclear or confusing. Pervasive errors. Absent or fundamentally flawed referencing.",
                    "min_score": 0,
                    "max_score": total_marks * 0.1 * 0.39
                }
            }
        }
    ]
    
    rubric_data = {
        "name": name,
        "total_marks": total_marks,
        "criteria": criteria,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = rubrics_collection.insert_one(rubric_data)
    rubric_data["_id"] = str(result.inserted_id)
    
    return {
        "success": True,
        "rubric": rubric_data
    }


@app.get("/api/rubrics")
async def list_rubrics():
    """List all uploaded rubrics."""
    rubrics = list(rubrics_collection.find({}, {"_id": 1, "name": 1, "total_marks": 1, "criteria": 1, "created_at": 1}))
    for r in rubrics:
        r["_id"] = str(r["_id"])
    return {"rubrics": rubrics}


@app.get("/api/rubric/{rubric_id}")
async def get_rubric(rubric_id: str):
    """Get a specific rubric by ID."""
    try:
        rubric = rubrics_collection.find_one({"_id": ObjectId(rubric_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid rubric ID format")
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    rubric["_id"] = str(rubric["_id"])
    return rubric


@app.delete("/api/rubric/{rubric_id}")
async def delete_rubric(rubric_id: str):
    """Delete a rubric by ID."""
    try:
        result = rubrics_collection.delete_one({"_id": ObjectId(rubric_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid rubric ID format")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return {"success": True, "message": "Rubric deleted"}


@app.post("/api/assess/single")
async def assess_single_submission(
    file: UploadFile = File(...),
    rubric_id: str = Form(...),
    student_id: str = Form(None)
):
    """Assess a single submission file."""
    
    # Get rubric
    rubric = rubrics_collection.find_one({"_id": ObjectId(rubric_id)})
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    
    # Save submission
    submission_path = UPLOAD_DIR / file.filename
    with open(submission_path, 'wb') as f:
        content = await file.read()
        f.write(content)
    
    # Extract text
    submission_text = extract_document_content(submission_path)
    if not submission_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from submission")
    
    # Run AI assessment
    assessment = await assess_with_ai(submission_text, rubric)
    assessment["student_id"] = student_id or submission_path.stem
    assessment["submission_file"] = file.filename
    assessment["rubric_id"] = str(rubric["_id"])
    assessment["rubric_name"] = rubric["name"]
    assessment["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    # Calculate percentage
    total_possible = rubric.get("total_marks", 100)
    total_score = assessment.get("total_score", 0)
    assessment["percentage"] = round((total_score / total_possible * 100) if total_possible > 0 else 0, 2)
    assessment["max_score"] = total_possible
    
    # Create annotated document
    if submission_path.suffix.lower() == '.docx':
        output_path = OUTPUT_DIR / f"{submission_path.stem}_GRADED.docx"
        annotate_docx_with_feedback(
            submission_path,
            output_path,
            assessment.get("annotations", []),
            assessment.get("overall_feedback", "")
        )
        assessment["annotated_file"] = str(output_path)
    
    # Store assessment
    result = assessments_collection.insert_one(assessment)
    assessment["_id"] = str(result.inserted_id)
    
    return assessment


@app.post("/api/assess/bulk")
async def assess_bulk_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    rubric_id: str = Form(...)
):
    """Process an eFundi zip file with multiple submissions."""
    
    # Get rubric
    rubric = rubrics_collection.find_one({"_id": ObjectId(rubric_id)})
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    
    # Save zip
    zip_path = UPLOAD_DIR / file.filename
    with open(zip_path, 'wb') as f:
        content = await file.read()
        f.write(content)
    
    # Create job
    job_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    job = {
        "job_id": job_id,
        "status": "processing",
        "rubric_id": str(rubric["_id"]),
        "rubric_name": rubric["name"],
        "zip_file": file.filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "progress": 0,
        "total": 0,
        "results": None
    }
    jobs_collection.insert_one(job)
    
    # Process in background
    async def process_job():
        try:
            output_dir = OUTPUT_DIR / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            results = process_efundi_zip(zip_path, rubric, output_dir)
            
            jobs_collection.update_one(
                {"job_id": job_id},
                {"$set": {
                    "status": "completed",
                    "results": results,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        except Exception as e:
            jobs_collection.update_one(
                {"job_id": job_id},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    
    background_tasks.add_task(process_job)
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "Processing started. Check /api/job/{job_id} for status."
    }


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a bulk assessment job."""
    job = jobs_collection.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/job/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Get the logs for a job."""
    job = jobs_collection.find_one({"job_id": job_id}, {"logs": 1, "_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"logs": job.get("logs", [])}


@app.get("/api/jobs")
async def list_jobs():
    """List all assessment jobs."""
    jobs = list(jobs_collection.find({}, {"_id": 0}).sort("created_at", -1).limit(50))
    return {"jobs": jobs}


@app.get("/api/download/{job_id}")
async def download_results(job_id: str):
    """Download the processed eFundi zip for a job."""
    job = jobs_collection.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    results = job.get("results", {})
    zip_path = results.get("output_zip_path")
    
    if not zip_path or not Path(zip_path).exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=Path(zip_path).name
    )


@app.get("/api/assessments")
async def list_assessments():
    """List recent assessments."""
    assessments = list(assessments_collection.find({}, {"_id": 1, "student_id": 1, "total_score": 1, "percentage": 1, "rubric_name": 1, "timestamp": 1}).sort("timestamp", -1).limit(100))
    for a in assessments:
        a["_id"] = str(a["_id"])
    return {"assessments": assessments}


@app.get("/api/assessment/{assessment_id}")
async def get_assessment(assessment_id: str):
    """Get a specific assessment."""
    try:
        assessment = assessments_collection.find_one({"_id": ObjectId(assessment_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid assessment ID format")
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    assessment["_id"] = str(assessment["_id"])
    return assessment


@app.get("/api/assessment/{assessment_id}/download")
async def download_annotated_document(assessment_id: str):
    """Download the annotated document for an assessment."""
    try:
        assessment = assessments_collection.find_one({"_id": ObjectId(assessment_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid assessment ID format")
    
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    annotated_file = assessment.get("annotated_file")
    if not annotated_file or not Path(annotated_file).exists():
        raise HTTPException(status_code=404, detail="Annotated document not found")
    
    return FileResponse(
        annotated_file,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(annotated_file).name
    )


# Webhook endpoint for eFundi
@app.post("/api/webhook/efundi")
async def efundi_webhook(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    rubric_id: str = Form(None),
    callback_url: str = Form(None)
):
    """Webhook to receive eFundi zip files for processing."""
    
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Use default rubric if not specified
    if not rubric_id:
        rubric = rubrics_collection.find_one({}, sort=[("created_at", -1)])
        if rubric:
            rubric_id = str(rubric["_id"])
        else:
            raise HTTPException(status_code=400, detail="No rubric available")
    
    # Same as bulk assess
    return await assess_bulk_zip(background_tasks, file, rubric_id)


# ===================== EFUNDI AUTOMATION =====================

# Store eFundi sessions
efundi_sessions = db["efundi_sessions"]

class EfundiCredentials(BaseModel):
    username: str
    password: str


class EfundiDownloadRequest(BaseModel):
    assignment_url: str
    rubric_id: str
    assignment_name: str = None  # Optional: to find specific assignment by name


@app.post("/api/efundi/authenticate")
async def efundi_authenticate(credentials: EfundiCredentials):
    """Authenticate with eFundi and save session."""
    if not PLAYWRIGHT_AVAILABLE:
        raise HTTPException(status_code=500, detail="Playwright not available for browser automation")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Go to eFundi login
            await page.goto("https://efundi.nwu.ac.za/portal", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            # Click login if needed
            login_link = page.locator("a:has-text('Login')")
            if await login_link.count() > 0:
                await login_link.first.click()
                await page.wait_for_timeout(2000)
            
            # Fill credentials - eFundi uses CAS/institutional login
            # Try to find username field
            username_field = page.locator("input[name='username'], input[id='username'], input[type='text']").first
            password_field = page.locator("input[name='password'], input[id='password'], input[type='password']").first
            
            await username_field.fill(credentials.username)
            await password_field.fill(credentials.password)
            
            # Submit
            submit_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Login'), button:has-text('Sign')").first
            await submit_btn.click()
            await page.wait_for_timeout(5000)
            
            # Check if login was successful by looking for user menu or dashboard elements
            if "portal" in page.url and "login" not in page.url.lower():
                # Save session state
                storage_state = await context.storage_state()
                
                # Store in database (encrypted in production)
                efundi_sessions.update_one(
                    {"username": credentials.username},
                    {"$set": {
                        "username": credentials.username,
                        "storage_state": storage_state,
                        "authenticated_at": datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
                
                await browser.close()
                return {"success": True, "message": "Successfully authenticated with eFundi"}
            else:
                await browser.close()
                raise HTTPException(status_code=401, detail="Authentication failed. Please check your credentials.")
                
    except Exception as e:
        print(f"[eFundi Auth Error] {e}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@app.get("/api/efundi/status")
async def efundi_status():
    """Check if we have a valid eFundi session."""
    session = efundi_sessions.find_one({}, sort=[("authenticated_at", -1)])
    if session:
        return {
            "authenticated": True,
            "username": session.get("username"),
            "authenticated_at": session.get("authenticated_at")
        }
    return {"authenticated": False}


@app.post("/api/efundi/debug-page")
async def efundi_debug_page(url: str = Form(...)):
    """Navigate to a URL and capture the page HTML and screenshot for debugging."""
    if not PLAYWRIGHT_AVAILABLE:
        raise HTTPException(status_code=500, detail="Playwright not available")
    
    session = efundi_sessions.find_one({}, sort=[("authenticated_at", -1)])
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=session["storage_state"])
            page = await context.new_page()
            page.set_default_timeout(30000)
            
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
            
            # Get page info
            title = await page.title()
            current_url = page.url
            
            # Get all links on the page
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a')).map(a => ({
                    text: a.innerText.trim().substring(0, 100),
                    href: a.href,
                    className: a.className
                })).filter(l => l.text.length > 0)
            }''')
            
            # Get all buttons
            buttons = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]')).map(b => ({
                    text: (b.innerText || b.value || '').trim().substring(0, 100),
                    type: b.type,
                    className: b.className
                })).filter(b => b.text.length > 0)
            }''')
            
            # Save screenshot
            debug_dir = OUTPUT_DIR / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = debug_dir / f"debug_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            await browser.close()
            
            # Filter for relevant links
            relevant_links = [l for l in links if any(kw in l['text'].lower() for kw in ['download', 'grade', 'assignment', 'submission', 'all'])]
            
            return {
                "title": title,
                "url": current_url,
                "screenshot": str(screenshot_path),
                "relevant_links": relevant_links[:20],
                "all_links_count": len(links),
                "buttons": buttons[:10]
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/efundi/download-and-assess")
async def efundi_download_and_assess(
    background_tasks: BackgroundTasks,
    request: EfundiDownloadRequest
):
    """Download assignment ZIP from eFundi and start assessment."""
    if not PLAYWRIGHT_AVAILABLE:
        raise HTTPException(status_code=500, detail="Playwright not available")
    
    # Get saved session
    session = efundi_sessions.find_one({}, sort=[("authenticated_at", -1)])
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated with eFundi. Please authenticate first.")
    
    # Verify rubric exists
    try:
        rubric = rubrics_collection.find_one({"_id": ObjectId(request.rubric_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid rubric ID")
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    
    # Create job
    job_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    job = {
        "job_id": job_id,
        "status": "starting",
        "rubric_id": str(rubric["_id"]),
        "rubric_name": rubric["name"],
        "assignment_url": request.assignment_url,
        "assignment_name": request.assignment_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "progress": 0,
        "total": 0,
        "results": None,
        "logs": []
    }
    jobs_collection.insert_one(job)
    
    def update_job_log(message):
        jobs_collection.update_one(
            {"job_id": job_id},
            {"$push": {"logs": {"time": datetime.now(timezone.utc).isoformat(), "message": message}}}
        )
        print(f"[Job {job_id}] {message}")
    
    def update_status(status):
        jobs_collection.update_one(
            {"job_id": job_id},
            {"$set": {"status": status}}
        )
    
    # Process in background
    async def download_and_process():
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(storage_state=session["storage_state"])
                page = await context.new_page()
                page.set_default_timeout(60000)  # 60 second timeout
                
                update_job_log("Starting browser automation...")
                update_status("navigating")
                
                assignment_url = request.assignment_url
                assignment_name = request.assignment_name
                
                # Step 1: Navigate to the site/tool URL
                update_job_log(f"Navigating to: {assignment_url}")
                await page.goto(assignment_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)
                
                # Save debug screenshot
                debug_dir = OUTPUT_DIR / "debug"
                debug_dir.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(debug_dir / f"{job_id}_01_initial.png"), full_page=True)
                update_job_log("Saved initial page screenshot")
                
                # Step 2: Click on "Assignments" in the left sidebar if we're not already there
                update_job_log("Looking for Assignments tab in sidebar...")
                assignments_selectors = [
                    "a.Mrphs-toolsNav__menuitem--link:has-text('Assignments')",
                    "li a:has-text('Assignments')",
                    ".Mrphs-toolsNav__menuitem span:has-text('Assignments')",
                    "a[title*='Assignments']"
                ]
                
                for selector in assignments_selectors:
                    try:
                        loc = page.locator(selector)
                        if await loc.count() > 0:
                            update_job_log(f"Found Assignments with: {selector}")
                            await loc.first.click()
                            await page.wait_for_timeout(3000)
                            break
                    except:
                        continue
                
                await page.screenshot(path=str(debug_dir / f"{job_id}_02_assignments_tab.png"), full_page=True)
                
                # Step 3: On the Assignments page, look for "Download All" directly
                # In eFundi, "Download All" is typically available from the assignments list page
                update_job_log("Looking for Download All on assignments page...")
                update_status("finding_download")
                
                # First, check if Download All is directly visible on the page
                download_all_found = False
                download_all_selectors = [
                    "a.assignment-item:has-text('Download All')",
                    "a[href*='doPrep_download_all']",
                    "a:has-text('Download All')",
                    "a[href*='downloadAll']",
                    "a.navIntraTool:has-text('Download')",
                    "span:has-text('Download All')",
                    "input[value='Download All']",
                    "button:has-text('Download All')"
                ]
                
                for selector in download_all_selectors:
                    try:
                        loc = page.locator(selector)
                        count = await loc.count()
                        update_job_log(f"Selector '{selector}' found {count} elements")
                        if count > 0:
                            update_job_log(f"Clicking Download All with: {selector}")
                            await loc.first.click()
                            await page.wait_for_timeout(3000)
                            download_all_found = True
                            break
                    except Exception as e:
                        update_job_log(f"Selector '{selector}' error: {e}")
                        continue
                
                # If Download All not found, we might need to navigate to a specific assignment first
                if not download_all_found:
                    update_job_log("Download All not directly visible, looking for assignment...")
                    
                    assignment_name = request.assignment_name
                    
                    if assignment_name:
                        update_job_log(f"Looking for assignment: {assignment_name}")
                        
                        # Try clicking on the assignment title
                        title_selectors = [
                            f"a:has-text('{assignment_name}')",
                            f"h4:has-text('{assignment_name}') a",
                            f"td:has-text('{assignment_name}') a"
                        ]
                        
                        for selector in title_selectors:
                            try:
                                loc = page.locator(selector).first
                                if await loc.count() > 0:
                                    update_job_log(f"Clicking assignment: {selector}")
                                    await loc.click()
                                    await page.wait_for_timeout(3000)
                                    break
                            except:
                                continue
                        
                        await page.screenshot(path=str(debug_dir / f"{job_id}_03_after_assignment_click.png"), full_page=True)
                        
                        # Now look for Download All again
                        for selector in download_all_selectors:
                            try:
                                loc = page.locator(selector)
                                if await loc.count() > 0:
                                    update_job_log(f"Found Download All with: {selector}")
                                    await loc.first.click()
                                    await page.wait_for_timeout(3000)
                                    download_all_found = True
                                    break
                            except:
                                continue
                
                await page.screenshot(path=str(debug_dir / f"{job_id}_04_download_page.png"), full_page=True)
                
                download_all_selectors = [
                    "a:has-text('Download All')",
                    "a.actionLink:has-text('Download')",
                    "a[href*='downloadAll']",
                    "span:has-text('Download All') a",
                    ".navIntraTool a:has-text('Download')"
                ]
                
                download_all_found = False
                for selector in download_all_selectors:
                    try:
                        loc = page.locator(selector)
                        if await loc.count() > 0:
                            update_job_log(f"Found Download All with: {selector}")
                            await loc.first.click()
                            await page.wait_for_timeout(3000)
                            download_all_found = True
                            break
                    except:
                        continue
                
                if not download_all_found:
                    # Maybe we're already on the download page, or it's in a different location
                    update_job_log("Download All link not found with standard selectors")
                    # Check if we can see the download options already
                    if await page.locator("input#selectall, input[value='all']").count() > 0:
                        update_job_log("Already on download options page")
                        download_all_found = True
                
                await page.screenshot(path=str(debug_dir / f"{job_id}_04_download_page.png"), full_page=True)
                
                if not download_all_found:
                    # Provide detailed error with page content
                    page_title = await page.title()
                    page_url = page.url
                    update_job_log(f"Page title: {page_title}, URL: {page_url}")
                    raise Exception(f"Could not find Download All. Check debug screenshots in {debug_dir}")
                
                # Step 5: Select download options
                update_job_log("Selecting download options...")
                update_status("selecting_options")
                
                # Check "All" checkbox
                all_checkbox = page.locator("input#selectall, input[type='checkbox'][name='selectall'], input[value='all']")
                if await all_checkbox.count() > 0:
                    await all_checkbox.first.check()
                    update_job_log("Checked 'All' checkbox")
                
                # Check "Student submission attachment(s)"
                student_attach = page.locator("input#withSubmission, input[name='withSubmission']")
                if await student_attach.count() > 0:
                    await student_attach.first.check()
                    update_job_log("Checked student submissions")
                
                # Check "Grade file"
                grade_file = page.locator("input#withGrade, input[name='withGrade']")
                if await grade_file.count() > 0:
                    await grade_file.first.check()
                    update_job_log("Checked grade file")
                
                # Select CSV format
                csv_radio = page.locator("input[type='radio'][value='csv'], input#csvFormat")
                if await csv_radio.count() > 0:
                    await csv_radio.first.check()
                    update_job_log("Selected CSV format")
                
                # Check "Feedback comments"
                feedback_comments = page.locator("input#withFeedbackText, input[name='withFeedbackText']")
                if await feedback_comments.count() > 0:
                    await feedback_comments.first.check()
                    update_job_log("Checked feedback comments")
                
                # Check "Feedback Attachment(s)"
                feedback_attach = page.locator("input#withFeedbackAttach, input[name='withFeedbackAttach']")
                if await feedback_attach.count() > 0:
                    await feedback_attach.first.check()
                    update_job_log("Checked feedback attachments")
                
                # Check "Include students who have not yet submitted"
                non_submit = page.locator("input#withoutSubmission, input[name='withoutSubmission']")
                if await non_submit.count() > 0:
                    await non_submit.first.check()
                    update_job_log("Checked include non-submitters")
                
                await page.wait_for_timeout(1000)
                await page.screenshot(path=str(debug_dir / f"{job_id}_05_options_selected.png"), full_page=True)
                
                # Step 6: Click Download button
                update_job_log("Clicking Download button...")
                update_status("downloading_zip")
                
                zip_path = UPLOAD_DIR / f"efundi_{job_id}.zip"
                
                # The download button is typically an input[type='submit'] or a button
                download_btn_selectors = [
                    "input[type='submit'][value='Download']",
                    "input.active[type='submit']",
                    "button:has-text('Download')",
                    "form input[type='submit']",
                    "input[name='eventSubmit_doDownload_all']"
                ]
                
                download_btn = None
                for selector in download_btn_selectors:
                    try:
                        loc = page.locator(selector)
                        if await loc.count() > 0:
                            download_btn = loc.first
                            update_job_log(f"Found Download button with: {selector}")
                            break
                    except:
                        continue
                
                if not download_btn:
                    await page.screenshot(path=str(debug_dir / f"{job_id}_06_no_download_btn.png"), full_page=True)
                    raise Exception("Could not find Download button")
                
                # Wait for download
                try:
                    async with page.expect_download(timeout=180000) as download_info:  # 3 min timeout
                        await download_btn.click()
                        update_job_log("Waiting for download to complete...")
                    
                    download = await download_info.value
                    await download.save_as(str(zip_path))
                    update_job_log(f"Downloaded ZIP to: {zip_path}")
                except Exception as e:
                    await page.screenshot(path=str(debug_dir / f"{job_id}_07_download_error.png"), full_page=True)
                    raise Exception(f"Download failed: {e}")
                
                await browser.close()
                
                # Step 7: Process the downloaded ZIP
                update_job_log("Processing downloaded submissions...")
                update_status("processing")
                jobs_collection.update_one(
                    {"job_id": job_id},
                    {"$set": {"zip_file": str(zip_path)}}
                )
                
                output_dir = OUTPUT_DIR / job_id
                output_dir.mkdir(parents=True, exist_ok=True)
                
                results = process_efundi_zip(zip_path, rubric, output_dir)
                update_job_log(f"Processed {results.get('submissions_processed', 0)} submissions")
                
                jobs_collection.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "status": "completed",
                        "results": results,
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                update_job_log("Job completed successfully!")
                
        except Exception as e:
            error_msg = str(e)
            print(f"[eFundi Download Error] {error_msg}")
            update_job_log(f"ERROR: {error_msg}")
            jobs_collection.update_one(
                {"job_id": job_id},
                {"$set": {
                    "status": "failed",
                    "error": error_msg,
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    
    background_tasks.add_task(download_and_process)
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "Download and assessment started. Check /api/job/{job_id} for status."
    }


@app.post("/api/efundi/upload-results/{job_id}")
async def efundi_upload_results(job_id: str, background_tasks: BackgroundTasks):
    """Upload graded results back to eFundi."""
    if not PLAYWRIGHT_AVAILABLE:
        raise HTTPException(status_code=500, detail="Playwright not available")
    
    # Get job
    job = jobs_collection.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    results = job.get("results", {})
    output_zip = results.get("output_zip_path")
    
    if not output_zip or not Path(output_zip).exists():
        raise HTTPException(status_code=404, detail="Output ZIP not found")
    
    # Get session
    session = efundi_sessions.find_one({}, sort=[("authenticated_at", -1)])
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated with eFundi")
    
    assignment_url = job.get("assignment_url")
    if not assignment_url:
        raise HTTPException(status_code=400, detail="Assignment URL not found in job")
    
    async def upload_to_efundi():
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(storage_state=session["storage_state"])
                page = await context.new_page()
                
                await page.goto(assignment_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                
                # Click Upload All
                upload_all = page.locator("a:has-text('Upload All')")
                if await upload_all.count() > 0:
                    await upload_all.first.click()
                    await page.wait_for_timeout(2000)
                
                # Upload file
                file_input = page.locator("input[type='file']").first
                await file_input.set_input_files(output_zip)
                
                # Click Upload button
                upload_btn = page.locator("button:has-text('Upload'), input[type='submit'][value='Upload']")
                await upload_btn.first.click()
                await page.wait_for_timeout(5000)
                
                await browser.close()
                
                jobs_collection.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "upload_status": "completed",
                        "uploaded_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                
        except Exception as e:
            jobs_collection.update_one(
                {"job_id": job_id},
                {"$set": {
                    "upload_status": "failed",
                    "upload_error": str(e)
                }}
            )
    
    background_tasks.add_task(upload_to_efundi)
    
    return {
        "success": True,
        "message": "Upload started. Results will be uploaded to eFundi."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
