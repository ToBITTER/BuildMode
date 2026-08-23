"""Create a realistic sample document for manual layout verification."""

from pathlib import Path
import site

site.addsitedir(str(Path(__file__).parent / ".deps"))

from docx_builder import build_docx
from pdf_builder import build_pdf


SAMPLE = {
    "full_name": "Amara Eze",
    "phone": "+234 801 234 5678",
    "email": "amara.eze@example.com",
    "linkedin": "www.linkedin.com/in/amara-eze",
    "education": [{"school": "University of Lagos", "location": "Lagos, Nigeria",
                   "dates": "Sep 2019 - Jul 2023", "degree": "B.Sc. Economics",
                   "detail": "First Class Honours"}],
    "work_experience": [{"organisation": "Northstar Advisory", "location": "Lagos, Nigeria",
                         "role": "Business Analyst", "dates": "Aug 2023 - Present",
                         "bullets": ["Built a market model that identified a NGN 450M growth opportunity.",
                                     "Presented weekly recommendations to senior client stakeholders."]}],
    "leadership_experience": [{"organisation": "Young Leaders Network", "location": "Lagos, Nigeria",
                               "role": "Programme Lead", "dates": "Jan 2022 - Jun 2023",
                               "bullets": ["Coordinated 18 volunteers to mentor 120 secondary-school students."]}],
    "certifications": ["Financial Modeling & Valuation Analyst, CFI"],
    "technical_skills": "Excel, Power BI, SQL, Python",
    "strengths": "Structured problem solving, communication, stakeholder management",
}

Path("sample_cv.docx").write_bytes(build_docx(SAMPLE).getvalue())
Path("sample_cv.pdf").write_bytes(build_pdf(SAMPLE).getvalue())
print("Created sample_cv.docx and sample_cv.pdf")
