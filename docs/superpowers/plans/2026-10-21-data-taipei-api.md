# Taipei API ingestion implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline.

**Goal:** Import the supplied resourceAquire JSON API through the existing normalization and idempotent case sync.

**Architecture:** Add a paginated HTTPX reader with system certificate validation. Extend sync-cases with an explicit api format and dry run, keeping CSV compatibility and loading all pages before a database transaction.

**Spec:** Existing procurement design §5 and the user's API URL in this chat.

**Constraints:** Never treat _importdate as an award date; keep append semantics; preserve source URL and resource ID; no secret output. Missing or inconsistent pages must fail rather than silently import a partial snapshot.

- [x] Write and run failing tests for pagination, count changes, repeated/empty pages, API errors, empty datasets, deterministic checksums, and normalization without invented dates.
- [x] Implement the API reader and CLI format/dry-run flags; isolate tests from local model credentials.
- [x] Verify unit tests, fetch all live rows, migrate the existing local database, import twice and confirm stable case counts.
- [x] Review the change, update README/progress, commit and push through the established workflow.

Verification: backend pytest 71/71; live API download 1043 rows; PostgreSQL migration 0001→0002; corrected import seen=1043/changed=1043, repeat seen=1043/changed=0; active corrected records=1043. Unit tests cover both fresh and legacy database migration. No bulk paid embedding calls were made in this step.

## Live data findings and rulings

- Real rows share official case numbers across agencies and award entries. Add nullable source_record_id via migration 0002; API identity uses resource ID + row _id, preserving original case numbers and all distinct rows. Existing CSV identity remains compatible. Cost: platform _id reassignments are not automatically reconciled across resource reloads.
- _importdate is publication ingestion time, not an award date. Dates remain null, so this source cannot satisfy five-year pricing eligibility. Multiple award entries are not guaranteed independent case-level comparables.
- Independent review reproduced an HTTPS→HTTP redirect bypass; a failing regression test was added, and redirects are now explicitly disabled on every request.
- Snapshot consistency checks are best effort: equal-count in-place updates cannot be ruled out without a publisher snapshot token.
- The first exploratory import used old case-number identities and produced 974 active rows from 1043 records. After importing corrected identities, only those exploratory records are soft-retired by exact source URL/period/known IDs. No existing unrelated rows are deleted.
