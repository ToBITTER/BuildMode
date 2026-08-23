# Deploying BuildMode

BuildMode is designed for container platforms and uses PostgreSQL in production. SQLite is only the local-development fallback.

## Render Blueprint

1. Push the `BuildMode` folder to a Git repository.
2. In Render, choose **New → Blueprint** and select the repository.
3. Render reads `render.yaml`, installs `requirements.txt`, starts Flask with Gunicorn, creates PostgreSQL, and injects `DATABASE_URL` and a generated `SECRET_KEY`.
4. After deployment, open `/_stcore/health` on the service URL to confirm the health check returns `ok`.

The included starter service and database plans are intentionally non-free because persistent applications should not sleep or discard user data. Adjust the plan names in `render.yaml` to match the plans available in your Render account.

If you created a Web Service manually instead of using the Blueprint, set these values in **Settings**:

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
- Health Check Path: `/health`

The Gunicorn target must be exactly `app:app`; `your_application.wsgi` is only a placeholder.

## Docker or another host

Build and start the image:

```bash
docker build -t buildmode .
docker run --rm -p 8501:8501 \
  -e DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DATABASE" \
  buildmode
```

The host must provide:

- `DATABASE_URL`: a PostgreSQL connection string.
- `PORT`: optional; defaults to `8501` in the image.
- HTTPS termination at the platform/load-balancer layer.

## Streamlit Community Cloud

Add this to the app's secrets configuration:

```toml
DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DATABASE"
```

Do not commit `.streamlit/secrets.toml`. The repository includes only a safe example.

## Data and security behavior

- Passwords are hashed with scrypt and a unique random salt; plaintext passwords are never stored.
- CV form content and generated files are processed in memory and are not persisted.
- Habit names, completion records, intentions and reflections are stored per user.
- Users can permanently delete their account and associated discipline records from the sidebar.
- Streamlit XSRF protection is enabled and uploads are limited to 5 MB.
- Generation input is bounded to reduce accidental or abusive resource use.

Before public launch, add a domain-specific privacy policy, terms of use, support email, database backups, uptime monitoring and platform-level rate limiting.
