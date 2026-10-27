# Security Notes

Open items carried forward for the Phase 3.2 security review. Not fixed yet —
tracked here so they aren't lost between now and then.

**Phase 3.2 fixed (not detailed here — see git history/tests):** a
non-superuser "Admin Staff" account could reset a superuser's password (and
change/delete a superuser account) via `/admin/`, a full privilege-escalation
path (`apps/accounts/admin.py`); the JWT login/refresh views, the portal
session login view, and the public registration endpoint had no rate
limiting; `Document.file` had no extension allowlist or size cap ahead of
in-memory PDF/DOCX parsing; a weak-password registration attempt surfaced as
an unhandled 500 instead of a 400.

## 1. `is_personal_question()` false-positive/no-fallback gap on the public `AskView`

**Where:** `apps/assistant/services/answering.py:9,58-66` (`is_personal_question`),
consumed by `apps/assistant/views.py`'s `AskView` (`permission_classes = [AllowAny]`)
and by `apps/portal/views.py::ask`.

**What it is:** A five-word regex (`\b(i|my|me|mine|myself)\b`) is the sole gate
deciding (a) whether a student's own record (`build_student_context` —
registration number, enrollments, attendance, **fee/financial balances**) gets
injected into the LLM prompt, and (b) whether the training-eligible or the
restricted (`ASSISTANT_LLM_CLIENT_PRIVATE`) client is used.

- **On the portal (`apps/portal/views.py::ask`)**: this heuristic only runs
  *after* `apps/portal/intents.py`'s keyword router has already tried to match
  one of ~10 specific personal intents. The router acts as a safety net for
  the router-miss case.
- **On the public DRF `AskView`**: there is no such router in front of it.
  Any JWT-authenticated caller that isn't going through the portal's HTML UI
  (e.g. a future mobile client, or a third-party integration) hits
  `is_personal_question()` directly and unassisted.

**Confirmed characteristics** (from the Frontend 2 code review, both verified
against the actual code):
- **False negative** — a personal question with no first-person pronoun
  ("current fee balance please") gets no personal context attached, even for
  an authenticated student who previously (pre-rework) always got their
  record attached. Functional regression for non-portal API consumers, not a
  leak (fails toward *less* helpful, not toward exposing data).
- **False positive** — a non-personal question phrased with "I"
  ("Which scholarships am I eligible for?", `apps/portal/tests/test_intents.py`'s
  own `test_scholarship_eligibility_has_no_matching_intent`) triggers
  `include_personal_context=True` and needlessly forces the restricted
  client, failing closed with `PERSONAL_DATA_UNAVAILABLE` if
  `ASSISTANT_LLM_CLIENT_PRIVATE` is unset (confirmed unset in this repo's dev
  `.env` today).

**Why it wasn't fixed in Frontend 2:** deliberately deferred — the portal's
own router closes the practical risk for the shipped UI; the public API's gap
is a known, scoped sharp edge to revisit with the rest of the assistant's
threat model in Phase 3.2, not a Frontend 2 blocker.

**What Phase 3.2 should decide:** whether the public `AskView` needs its own
fallback layer (reuse a version of the portal's intent router, or a different
mechanism), and whether the false-positive class is acceptable as "fails
closed, not open" or needs tightening.

**Phase 3.2 update:** reassessed and confirmed to fail safe on both edges —
the false-negative (no pronoun) only under-triggers personal context
(unhelpful, not a leak), and the false-positive (`"...am I..."`) only
over-triggers the restricted client / fail-closed path (over-restrictive,
not a leak). Not a privacy defect. Still deferred, not fixed: the practical
gap (non-portal API callers get no template-answer fallback) remains, with
the same proposed fix as above (reuse `apps.portal.intents.detect_intent` in
front of `AskView`).

## 2. Seeded `demo_student` account must not reach production

**Where:** `apps/portal/management/commands/seed_portal_demo.py`.

**What it is:** A management command (added for manual browser QA of the
student portal) that creates/refreshes a login with:
- username `demo_student`
- password `DemoPass123` (hardcoded in the command)
- name "Laiba Ishaq", registration no. `2026-CS-042`, enrolled in real
  BSCS subjects with seeded attendance and fee data.

This is a real, working login with a publicly-known password once the
command has been run. It is intended for local/dev use only.

**What Phase 3.2 (or deploy prep, whichever comes first) must verify:**
- `seed_portal_demo` is never invoked as part of any production deployment
  or migration step (it isn't currently wired into any automated
  deploy/release script as of this writing — confirm that stays true).
- If a production database was ever seeded from a dev snapshot or dump that
  included this account, delete the `demo_student` `User`/`StudentProfile`
  row (and its `Enrollment`/`Attendance`/`FeeStatus` rows) before go-live.
- Consider adding a startup/deploy-time check that fails loudly if a user
  named `demo_student` exists when `DJANGO_SETTINGS_MODULE=config.settings.prod`.

## 3. `DocumentAdmin` doesn't override `has_change_permission` for catalog-synced documents

**Where:** `apps/assistant/admin.py` (`DocumentAdmin`).

**What it is:** Catalog-synced documents (`source_content_type_id is not
None`) are made fully read-only via `get_readonly_fields` and non-deletable
via `has_delete_permission`, but `has_change_permission` is never overridden
alongside them, so Django still reports the object as "changeable" via the
default permission check (which only looks at the model-level
`change_document` permission, ignoring the object).

**Confirmed characteristic:** Django's `submit_row` template tag keys the
Save button's visibility off `has_change_permission`, not off whether
`readonly_fields` happens to cover every field — so the Save button still
renders on a catalog-synced document's change page even though every field on
it is readonly. Clicking it is a no-op for content (no fields are bound to
change), but it still calls `obj.save()`, which bumps `updated_at`
(`BaseModel`'s `auto_now`) and creates a `LogEntry` — a misleading admin
history entry, not a data-integrity issue.

**Why not fixed now:** low practical impact (no data changes), scoped out of
the batch of fixes this was found alongside. Tracked here rather than fixed
silently so it isn't lost.

**What to do:** override `has_change_permission(self, request, obj=None)` to
return `False` (or "view only") for catalog-synced documents, matching the
existing `has_delete_permission` pattern, so the Save button and the
permission API agree with what `get_readonly_fields` already enforces.

## 4. `DocumentAdmin.save_model`'s add path leaves the in-memory `obj` half-populated

**Where:** `apps/assistant/admin.py`, `DocumentAdmin.save_model`.

**What it is:** On create, `save_model` calls
`apps.assistant.services.create_document(...)` (which does the actual
insert + queues ingestion) and then only patches `obj.pk = document.pk` onto
the in-memory form instance before returning — it never calls
`super().save_model()` and never copies back any other field (`status`,
`content_hash`, `error`, `source_url`, timestamps) that `create_document`
actually persisted. Every other attribute on `obj` reflects unsaved form
defaults, not the real database row.

**Confirmed characteristic:** currently inert. `Document` has no inline or
m2m fields, so `save_related`'s `form.save_m2m()`/formset handling is a
no-op; `log_addition` and `response_add` only consume `obj.pk` and `str(obj)`
(`Document.__str__` returns `title`, which is correctly set on `obj`
already); and any `_continue` redirect re-fetches the object fresh from the
database on the next `GET`. Nothing today reads the stale fields.

**Why not fixed now:** no live bug to reproduce a regression test against;
fixing it speculatively for a scenario that doesn't exist yet risks its own
mistakes. Tracked here as a landmine to defuse before it becomes live.

**What to watch for / what to do:** if `DocumentAdmin` ever gains an inline,
an m2m field, or any post-`save_model` logic that reads fields off `obj`
directly (rather than re-querying), copy the real persisted fields back onto
`obj` after calling `create_document` (or just call `super().save_model()`
with `document`'s field values already applied to `obj` before saving,
rather than swapping in a separately-created row).

## 5. `sync_admin_access` leaves a dangling `AdminProfile` on demotion

**Where:** `apps/accounts/services.py::sync_admin_access`.

**What it is:** Promoting a user to `role=admin` creates an `AdminProfile`
row; demoting them back to `role=student` clears `is_staff` and removes them
from the "Admin Staff" group, but never deletes the now-orphaned
`AdminProfile`. Not a security issue — `AdminProfile` carries no permissions
of its own (authorization runs entirely on `role` + group membership, per
`apps.core.admin.UniversityAdminSite.has_permission` and `IsAdminStaff`), and
`get_current_user_profile` keys strictly on the user's current `role`, so a
demoted student's stale `AdminProfile` is never read. Cleanliness/data-hygiene
only: a re-promotion later hits `get_or_create` and reuses the stale row
rather than erroring, so there's no crash either.

**What to do, if anyone gets to it:** delete the `AdminProfile` in the
`else` branch of `sync_admin_access` alongside clearing `is_staff`/the group.
