# RBAC Explorer Systemic Design Fix Plan

This plan covers the main backend and frontend weaknesses found during the systemic design review. The most important issue is that the app has authentication, but it does not yet have project ownership or tenant isolation. Until that is fixed, the app should be treated as single-user only.

## Phase 1: Project Ownership And Auth

- Add `owner_user_id` to `Project` in `backend/app/models.py`.
- Add an Alembic migration for `projects.owner_user_id`, indexed and non-null for new projects.
- Update `create_project()` to inject `current_user = Depends(get_current_user)` and persist `owner_user_id=current_user`.
- Replace all project lookups like `select(Project).where(Project.slug == slug)` with a shared helper:

  ```python
  async def get_project_for_user_or_404(slug, user_id, session):
      ...
  ```

- Apply that helper across `projects`, `roles`, `permissions`, `resources`, `simulate`, `analyze`, `export`, and `import`.
- Decide whether slugs are globally unique or per-user unique:
  - simplest: keep global unique slugs;
  - better UX: unique constraint on `(owner_user_id, slug)`.
- Add backend tests proving user A cannot list, read, mutate, clean, export, or delete user B's project.

## Phase 2: Clerk JWT Hardening

- Add settings for `clerk_issuer`, `clerk_audience`, and optionally allowed `azp`.
- Change `backend/app/auth.py` to verify issuer and audience instead of using `verify_aud=False`.
- Add timeout handling to JWKS fetches.
- Add JWKS cache expiry or refresh-on-key-miss behavior.
- Make auth failures consistently return `401`, not upstream `500` if Clerk/JWKS is temporarily unavailable.
- Add tests for missing token, invalid token, wrong issuer, wrong audience, and missing `sub`.

## Phase 3: Centralize Backend Access Control

- Create `backend/app/dependencies.py` or `backend/app/security.py`.
- Move shared helpers there:
  - `get_current_user`
  - `get_project_for_user_or_404`
  - `get_role_for_project_or_404`
  - `get_permission_for_project_or_404`
  - `get_resource_for_project_or_404`
- Delete duplicated `_get_project()` and `get_project_or_404()` helpers from routers.
- Make every route take `current_user` explicitly, including read-only routes.
- Add tests for object-level authorization on every route family.

## Phase 4: Import Safety

- Reuse normal schema validation inside imports.
- For CSV import:
  - validate `method` and `path` through `ResourceCreate`;
  - count invalid rows separately;
  - return `{created, skipped, invalid, processed}`.
- For OpenAPI import:
  - validate `paths` is a dict;
  - validate each method/path through `ResourceCreate`;
  - cap number of methods as well as path count;
  - reject malformed path entries rather than crashing.
- For YAML import:
  - validate top-level shape before mutating the DB;
  - enforce max roles, max permissions, and max inheritance edges;
  - call the same cycle-detection logic used by manual parent creation;
  - reject cycles before commit.
- Wrap imports in one transaction and rollback fully on validation failure.

## Phase 5: Recursive Query And Graph Safety

- Fix YAML cycle insertion first, then add database/application safeguards.
- Add a max inheritance depth policy, for example `32`.
- Update recursive CTEs in simulation, analysis, and diff to include depth tracking.
- Add tests for:
  - valid inheritance chains;
  - attempted cycles through API;
  - attempted cycles through YAML import;
  - deep hierarchy rejection or truncation behavior.
- Consider adding indexes beyond FK indexes if query plans show slow scans on larger data.

## Phase 6: Diff Correctness

- Fix `backend/app/routers/analyze.py` so `before_ids` represents the actual current state:

  ```python
  before_ids = await resolve_allowed_resource_ids(set(), set())
  after_ids = await resolve_allowed_resource_ids(
      set(add_permissions),
      set(remove_permissions),
  )
  ```

- Add tests where removing an existing permission produces `lost`.
- Add tests where adding and removing permissions together produce correct `gained`, `lost`, and unchanged counts.
- Rename the module or split `diff` out of `analyze.py` later if it grows.

## Phase 7: Frontend API Consistency

- Add `exportYaml()` to `frontend/src/api/export_.js`.
- Replace the direct `fetch` in `frontend/src/tabs/GraphTab.jsx` with the shared axios client.
- Ensure downloads support blob responses through axios.
- Add a global axios response interceptor for `401` and `403`.
- Clear auth token on sign-out or when `isSignedIn` becomes false.

## Phase 8: Frontend Mutation Reliability

- Update `frontend/src/tabs/PermissionsTab.jsx` to await assignment and mapping calls.
- Add per-row loading state for assign/map/delete.
- Refresh data after successful assign/map/delete.
- Surface user-visible errors instead of silent failures.
- Disable duplicate actions while a request is in flight.
- Apply the same pattern to roles, resources, graph parent changes, imports, and clean actions.

## Phase 9: UX And Product Consistency

- Fix the YAML example in `frontend/src/tabs/ImportTab.jsx` so it matches the backend's actual accepted format, or change the backend to support the documented format.
- Replace browser `confirm()` for destructive actions with an app modal requiring typed slug confirmation.
- Add a project-level "last updated" or audit trail if this will be used by teams.
- Add empty states for roles, permissions, resources, graph, simulator, and analysis.
- Add consistent success/error toast or inline message handling.

## Phase 10: Testing And CI

- Fix local toolchain first:
  - install backend test dependencies from `backend/requirements-dev.txt`;
  - replace the bad local Node binary or reinstall Node for this machine.
- Add backend test groups:
  - auth and tenant isolation;
  - import validation;
  - cycle detection;
  - diff correctness;
  - destructive endpoint safeguards.
- Add frontend tests:
  - export uses axios client;
  - assignment/mapping refreshes after success;
  - errors render visibly;
  - import examples match supported format.
- Add CI commands:
  - `cd backend && pytest`
  - `cd backend && ruff check .`
  - `cd frontend && npm run lint`
  - `cd frontend && npm test -- --run`
  - `cd frontend && npm run build`

## Suggested Fix Order

1. Ownership model and scoped project helper.
2. Route-by-route authorization tests.
3. Clerk JWT hardening.
4. Import cycle/schema fixes.
5. Diff correctness.
6. Frontend axios/export/mutation cleanup.
7. UX polish and docs.
8. CI.

## Release Blockers

- Project ownership and backend query scoping must be completed before multi-user deployment.
- Clerk JWT verification must enforce issuer and audience before production use.
- YAML import must reject cycles before recursive graph endpoints can be considered safe.
