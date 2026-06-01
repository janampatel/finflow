# Deployment — Docker · GitHub Actions · Cloud Run

The serving layer is **stateless**, so it containerizes cleanly and scales to N
replicas. The same image runs locally and on Cloud Run.

> **Approach:** the `Dockerfile`, CI pipeline, and deploy workflow are real and
> validated by `docker build` in CI. Going live is a **single command** (Step 3)
> — no idle billing, no cold-start risk in a demo window.

Set your project id once; every command below reuses it:

```powershell
$PROJECT_ID = "your-project-id"
```

---

## 1. Prerequisites (one-time)

- **gcloud CLI** — `winget install --id Google.CloudSDK -e`, then restart the shell.
- A **GCP project** with **billing enabled** (free tier + student credits cover this).

```powershell
gcloud auth login
gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

---

## 2. Run locally

```powershell
# Single container (boots without data — /health works immediately)
docker build -t finflow-api:local .
docker run --rm -p 8000:8080 -e GROQ_API_KEY=$env:GROQ_API_KEY finflow-api:local

# Or the full stack (API + Next.js frontend)
docker compose up --build
# API http://localhost:8000  ·  Frontend http://localhost:3000
```

---

## 3. Deploy to Cloud Run — one command

```powershell
gcloud run deploy finflow-api `
  --source . --region us-central1 --allow-unauthenticated `
  --memory 2Gi --cpu 2 --timeout 300 --max-instances 3 `
  --set-env-vars "GROQ_API_KEY=$env:GROQ_API_KEY,FRONTEND_ORIGINS=*"
```

`--source .` makes Cloud Build compile the `Dockerfile`, push to Artifact
Registry, and roll out a scale-to-zero HTTPS revision. The command prints the
public URL; verify with `curl <url>/health`.

---

## 4. Deploy from CI (optional)

`.github/workflows/deploy-cloudrun.yml` runs the same deploy on demand
(**Actions → Deploy to Cloud Run → Run workflow**). Add these repo secrets
(**Settings → Secrets and variables → Actions**):

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | your project id |
| `GCP_SA_KEY` | service-account JSON key (roles: `run.admin`, `cloudbuild.builds.editor`, `artifactregistry.writer`, `iam.serviceAccountUser`) |
| `GROQ_API_KEY` | Groq LLM key (injected as a Cloud Run env var) |

> Production: prefer **Workload Identity Federation** (keyless) over a JSON key —
> `google-github-actions/auth@v2` supports it.

---

## Why the image carries no data

The feature store (6.3M Parquet rows + FinBERT + a RandomForest model) is too
large to bake into a lean image, and `data/` is gitignored. The image ships
**code only** and boots fine without it. For corpus-backed endpoints, choose:

- **Local** — `docker compose` mounts `./data` read-only (already wired).
- **Live demo** — bake a ~50–100k-row Parquet sample before `docker build`.
- **Production** — point DuckDB at a Cloud Storage bucket (`httpfs`); no data in
  the image at all.

**Stateless compute, externalized state** is exactly what lets the service scale
horizontally.
