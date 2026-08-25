# TRAQ — Career & Discipline Studio

A deployable Flask web service with a custom vanilla HTML/CSS/JavaScript interface and two tools:

- **CV Studio** creates a clean, consulting-style CV from repeatable form sections and exports both editable Word and ready-to-send PDF files.
- **Discipline System** turns the supplied journal layouts into an interactive daily habit and reflection dashboard.

## Setup

Python 3.10 or newer is recommended.

```bash
pip install -r requirements.txt
python app.py
```

Open the app at `http://localhost:5000`.

Local mode stores accounts and discipline data in `traq.db`. A Render deployment refuses to start without `DATABASE_URL`, preventing user accounts from being silently stored on Render's disposable filesystem. See [DEPLOYMENT.md](DEPLOYMENT.md) for PostgreSQL setup.

## CV generation

Fill in only the sections you need and select **Generate CV**. Empty sections are omitted from the Word document. The generated `.docx` remains editable in Microsoft Word, LibreOffice, or Google Docs.

The PDF is generated directly by TRAQ, so LibreOffice is not required. New users receive an integrated walkthrough on first launch and can reopen it at any time from the sidebar.

The document-building code is isolated in `docx_builder.py` and `pdf_builder.py`, so it can be tested without Streamlit:

```python
from docx_builder import build_docx

output = build_docx({"full_name": "Ada Okafor", "education": []})
with open("Ada_Okafor_CV.docx", "wb") as file:
    file.write(output.getvalue())
```

## Notes

TRAQ includes secure user accounts and database-backed habit history. CV form values and generated documents are intentionally kept in memory rather than stored. Its interface is handcrafted with vanilla HTML, CSS and JavaScript, with Driver.js powering the integrated tour. PostgreSQL is required for durable production deployment; SQLite is only the local fallback.
