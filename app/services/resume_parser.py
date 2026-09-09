"""Small, local resume parser used to prefill candidate onboarding forms."""
from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path


COURSES = ["M.Tech", "M.E", "MBA", "MCA", "M.Sc", "B.Tech", "B.E", "BCA", "B.Sc", "B.Com", "B.A", "Diploma", "PhD"]
SPECIALIZATIONS = [
    "Information Technology", "Computer Science", "Electrical Engineering", "Electronics and Communication",
    "Mechanical Engineering", "Civil Engineering", "Data Science", "Business Administration", "Finance", "Marketing",
]
SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "SQL", "FastAPI", "Django", "Flask", "React", "Angular",
    "Node.js", "Spring Boot", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "Power BI", "Excel",
    "Machine Learning", "Data Analysis", "C++", "C#", ".NET", "HTML", "CSS", "MongoDB", "PostgreSQL",
]
TITLES = [
    "Senior Software Engineer", "Software Engineer", "Software Developer", "Python Developer", "Java Developer",
    "Data Engineer", "Data Analyst", "Business Analyst", "Project Manager", "Product Manager", "DevOps Engineer",
    "Full Stack Developer", "Frontend Developer", "Backend Developer", "Team Lead", "Consultant",
]
CITIES = ["New Delhi", "Delhi", "Mumbai", "Bengaluru", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata", "Noida", "Gurugram", "Gurgaon", "Meerut"]


def _document_text(path: Path, extension: str) -> str:
    if extension == ".docx":
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        xml = re.sub(r"</w:p[^>]*>", "\n", xml)
        return html.unescape(re.sub(r"<[^>]+>", "", xml))
    if extension == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    raw = path.read_bytes()
    return max((raw.decode("utf-8", errors="ignore"), raw.decode("utf-16le", errors="ignore"), raw.decode("latin-1", errors="ignore")), key=len)


def _first_match(options: list[str], text: str) -> str:
    return next((option for option in options if re.search(r"(?<!\w)" + re.escape(option) + r"(?!\w)", text, re.I)), "")


def _month_value(value: str) -> str:
    months = {name[:3].lower(): index for index, name in enumerate(
        ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
    numeric = re.search(r"(0?[1-9]|1[0-2])[/.-](19\d{2}|20\d{2})", value)
    if numeric:
        return f"{numeric.group(2)}-{int(numeric.group(1)):02d}"
    named = re.search(r"(" + "|".join(months) + r")[a-z]*\s+(19\d{2}|20\d{2})", value, re.I)
    return f"{named.group(2)}-{months[named.group(1).lower()[:3]]:02d}" if named else ""


def extract_resume_profile(path: Path, extension: str) -> dict:
    text = _document_text(path, extension)
    clean = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip(" \t|•·-") for line in clean.splitlines() if line.strip(" \t|•·-")]
    course = _first_match(COURSES, clean)
    specialization = _first_match(SPECIALIZATIONS, clean)
    institution_index = next((index for index, line in enumerate(lines) if re.search(r"\b(university|college|institute|iit|nit)\b", line, re.I)), None)
    institution = lines[institution_index] if institution_index is not None else ""
    education_context = " ".join(lines[max(0, (institution_index or 0) - 4):(institution_index or 0) + 5])
    education_years = re.findall(r"\b(?:19|20)\d{2}\b", education_context)
    qualification = "Doctorate / PhD" if course == "PhD" else "Post graduation" if course.startswith(("M.", "MBA", "MCA")) else "Diploma" if course == "Diploma" else "Graduation" if course else ""
    title = _first_match(TITLES, clean)
    company_index = next((index for index, line in enumerate(lines) if re.search(r"\b(pvt\.?\s*ltd|limited|technologies|solutions|systems|company|inc\.?|llp)\b", line, re.I)), None)
    company = lines[company_index] if company_index is not None else ""
    work_context = " ".join(lines[max(0, (company_index or 0) - 3):(company_index or 0) + 5])
    dates = re.findall(r"(?:0?[1-9]|1[0-2])[/.-](?:19|20)\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(?:19|20)\d{2}", work_context, re.I)
    experience = re.search(r"(\d{1,2})(?:\.\d+)?\+?\s*(?:years?|yrs?)\b", clean, re.I)
    education = {}
    if course or institution:
        education = {"qualification": qualification, "institution_name": institution, "course": course,
                     "specialization": specialization, "course_type": "Full time",
                     "start_year": education_years[0] if education_years else "",
                     "end_year": education_years[-1] if education_years else ""}
    work = {}
    if company or title:
        work = {"company_name": company, "job_title": title, "employment_type": "Full time",
                "start_date": _month_value(dates[0]) if dates else "",
                "end_date": "" if re.search(r"\bpresent\b", work_context, re.I) else (_month_value(dates[-1]) if len(dates) > 1 else ""),
                "is_current": bool(re.search(r"\bpresent\b", work_context, re.I))}
    return {"city": _first_match(CITIES, clean), "current_title": title,
            "total_experience": float(experience.group(1)) if experience else 0,
            "skills": [skill for skill in SKILLS if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", clean, re.I)],
            "highest_qualification": qualification, "education_specialization": specialization,
            "graduation_year": education.get("end_year", ""), "education_history": [education] if education else [],
            "work_experiences": [work] if work else []}
