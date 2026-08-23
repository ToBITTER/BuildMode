# BuildMode — Career & Discipline Studio

A local Streamlit web app with two tools:

- **CV Studio** creates a clean, consulting-style CV from repeatable form sections and exports both editable Word and ready-to-send PDF files.
- **Discipline System** turns the supplied journal layouts into an interactive daily habit and reflection dashboard.

## Setup

Python 3.10 or newer is recommended.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit opens the app in your browser, normally at `http://localhost:8501`.

Local mode stores accounts and discipline data in `buildmode.db`. For a deployed multi-user service, set `DATABASE_URL` to PostgreSQL. See [DEPLOYMENT.md](DEPLOYMENT.md) for Render, Docker and Streamlit Community Cloud instructions.

## CV generation

Fill in only the sections you need and select **Generate CV**. Empty sections are omitted from the Word document. The generated `.docx` remains editable in Microsoft Word, LibreOffice, or Google Docs.

The PDF is generated directly by BuildMode, so LibreOffice is not required. New users receive a four-step walkthrough on first launch and can reopen it at any time from the sidebar.

The document-building code is isolated in `docx_builder.py` and `pdf_builder.py`, so it can be tested without Streamlit:

```python
from docx_builder import build_docx

output = build_docx({"full_name": "Ada Okafor", "education": []})
with open("Ada_Okafor_CV.docx", "wb") as file:
    file.write(output.getvalue())
```

## Notes

BuildMode includes secure user accounts and database-backed habit history. CV form values and generated documents are intentionally kept in memory rather than stored. PostgreSQL is required for durable production deployment; the automatic SQLite fallback is intended only for local development.
