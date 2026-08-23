"""Standalone smoke tests for the Word generator."""

from io import BytesIO
from pathlib import Path
import site
from zipfile import ZipFile

site.addsitedir(str(Path(__file__).parent / ".deps"))

from docx_builder import build_docx
from pdf_builder import build_pdf


def _is_docx(value: BytesIO) -> bool:
    value.seek(0)
    with ZipFile(value) as archive:
        return "word/document.xml" in archive.namelist()


def test_empty_repeatable_sections_do_not_crash() -> None:
    output = build_docx({
        "full_name": "Test Person",
        "education": [],
        "work_experience": [],
        "leadership_experience": [],
        "certifications": [],
    })
    assert _is_docx(output)


def test_realistic_cv_is_a_valid_docx() -> None:
    output = build_docx({
        "full_name": "Amara Eze",
        "phone": "+234 801 234 5678",
        "email": "amara.eze@example.com",
        "linkedin": "linkedin.com/in/amara-eze",
        "education": [{"school": "University of Lagos", "location": "Lagos, Nigeria",
                       "dates": "Sep 2019 - Jul 2023", "degree": "B.Sc. Economics",
                       "detail": "First Class Honours"}],
        "work_experience": [{"organisation": "Northstar Advisory", "location": "Lagos, Nigeria",
                             "role": "Business Analyst", "dates": "Aug 2023 - Present",
                             "bullets": ["Built a market model that identified a NGN 450M growth opportunity.",
                                         "Presented weekly recommendations to senior client stakeholders."]}],
        "leadership_experience": [],
        "certifications": ["Financial Modeling & Valuation Analyst, CFI"],
        "technical_skills": "Excel, Power BI, SQL, Python",
        "strengths": "Structured problem solving, communication, stakeholder management",
    })
    assert _is_docx(output)


def test_pdf_handles_empty_repeatable_sections() -> None:
    output = build_pdf({"full_name": "Test Person", "education": [], "work_experience": [],
                        "leadership_experience": [], "certifications": []})
    assert output.getvalue().startswith(b"%PDF-")


if __name__ == "__main__":
    test_empty_repeatable_sections_do_not_crash()
    test_realistic_cv_is_a_valid_docx()
    test_pdf_handles_empty_repeatable_sections()
    print("All document builder tests passed.")
