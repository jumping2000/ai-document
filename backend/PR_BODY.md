Summary

Persist workflow state transitions to DB, add migration, integration test, and fixes.

Key changes

- `backend/app/workflows/execution/runner.py` — persist states + guard fatal trigger
- `backend/app/api/routes/workflow.py` — use DB for start/get/approve/retry
- `backend/app/db/models.py` — `owner_id` made nullable
- `backend/app/db/__init__.py` — export `session` for tests
- `backend/app/tests/test_workflow_persistence.py` — integration test + ASGITransport fix
- `backend/alembic/versions/20260523_001_initial_workflows.py` — migration skeleton
- `backend/pyproject.toml` — hatch build config for editable installs

Verification

1. From `backend/`:

```powershell
uv pip install -r requirements-dev.txt
uv run pytest -q
```

Expected: `34 passed` (full suite)

Notes

- The branch contains additional test stubs and small fixes to make tests run in an isolated environment.
- Migration should be reviewed before applying to production Postgres (timestamps/defaults, UUID types).