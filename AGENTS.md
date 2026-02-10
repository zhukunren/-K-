# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI service plus ML pipeline, training, and prediction scripts (for example `api_full.py`, `pipeline_core.py`, `train_model.py`).
- `frontend/`: Vue 3 + Vite app (`src/` for UI, `src/api/` for HTTP calls, `src/router/`, `src/components/`, `src/styles/`).
- `logs/`: runtime and autostart logs.
- `requirements.txt` and `frontend/package.json`: dependency manifests. `venv/` is a local virtual environment and should not be committed.

## Architecture Overview
- `backend/api_full.py` exposes the FastAPI endpoints and calls the ML pipeline (`backend/pipeline_core.py`) plus cache helpers (`backend/model_cache.py`).
- The Vue 3 frontend proxies `/api` to `http://localhost:8001` via `frontend/vite.config.js` and renders UI with Element Plus.

## Build, Test, and Development Commands
Backend (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe backend\api_full.py
```

Frontend:
```powershell
cd frontend
npm install
npm run dev
```

Build frontend bundle:
```powershell
cd frontend
npm run build
```

Root-level helper scripts (`.ps1`/`.bat`) exist for Windows one-click start/stop; prefer the explicit commands above for development.

## Coding Style & Naming Conventions
- Python: 4-space indentation, PEP 8 style, `snake_case` for functions/modules.
- JavaScript/Vue: 2-space indentation, ES modules, `PascalCase` for Vue components (for example `MiniKline.vue`).
- Keep API clients in `frontend/src/api/` and general helpers in `frontend/src/utils/`.
- Avoid adding large binary outputs to the repo; write runtime artifacts to `logs/`.

## Testing Guidelines
No automated test suite is present. Use manual smoke checks:
- Backend: open `http://localhost:8001/docs` after starting `api_full.py`.
- Frontend: open `http://localhost:5173` after `npm run dev`.
If you add tests, place them under `backend/tests/` or `frontend/tests/` and document the runner and how to execute it.

## Commit & Pull Request Guidelines
- Git history uses short, descriptive commit messages; many are in Chinese, so match the existing language and keep a single-line summary.
- Pull requests should include: summary of changes, how to run/verify, and screenshots for UI changes.

## Operations & Autostart
- Use the root-level PowerShell autostart install/uninstall scripts to register or remove the Scheduled Task `AutoStart-SimilarKLine`.
- Autostart logs live in `logs/` (for example `logs/autostart-frontend.out.log` and `.err.log`).

## Security & Configuration Tips
- If you add data-provider tokens, keep them in environment variables or a local untracked file; do not commit credentials.

## Configuration Notes
- Default ports: backend `8001`, frontend `5173`. Update `backend/api_full.py` and `frontend/vite.config.js` together if you change ports.
- Autostart uses a Windows Scheduled Task (name `AutoStart-SimilarKLine`) and writes to `logs/autostart*.log`.
