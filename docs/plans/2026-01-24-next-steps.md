# Next Steps (Post v0.1.0)

## Current State
- Repo cleaned and worktrees removed; development continues in main workspace.
- ATOM01 GLB assets moved under `/public/models/robots/atom01` with a manifest.
- Frontend model base path is now configurable via `VITE_MODEL_BASE_URL`.

## Short-Term (1–2 weeks)
1. **Robot selection UX**
   - Add UI to select robotId (default `atom01`).
   - Persist selection (localStorage or user profile).
2. **Model registry**
   - Add `robots.json` registry describing available robots + manifests.
   - Load registry at app start and validate on selection.
3. **Asset build pipeline**
   - Document GLB conversion pipeline (from `robot/` source to `public/models/robots/<id>`).

## Mid-Term (2–4 weeks)
1. **External model storage**
   - Replace static `/models` with external asset service (DB/CDN + signed URL).
   - Keep `VITE_MODEL_BASE_URL` as the switch for dev vs prod.
2. **Backend model service (optional)**
   - Add an API endpoint to fetch model manifests by robotId.

## Long-Term
- Support multiple robot variants with per-tenant access control.
- Model versioning and caching strategy.

