# Metro budgets and procurement procedures

**Goal:** Import the official 2026-10 metro resource and index two currently listed PCC procedure PDFs, then verify budget filtering and page citations with real API calls.

**Plan:** Execute inline using TDD for adapter/CLI/UI changes. PDF source research is independent and read-only; final implementation review checks the integrated change.

**Source decisions:**

- Metro resource `69fe3257-3e97-4386-8a8c-f760586f5be9` has 52 rows with 標案名稱/預算金額/標的分類/統計期_民國年月. No agency or official case number is present. Agency is the known publishing company; row sequence is not an official case number. Unknown budgets stay null.
- 統計期 is the source reporting month, not an actual tender/award date. Preserve source_period, leave missing actual dates null. API row IDs change by monthly resource, so metro uses the existing agency/name/year identity instead of the work-bureau award-row identity.
- Replace the 2012 Taipei handbook, whose source explicitly restricts reuse, with PCC JP01 (6 pages, revision 2024-10-18) and JP03 (5 pages, version listed 2021-12). Attribute the PCC source and website open-data declaration; these are source versions, not a guarantee of current law in every circumstance.

- [x] Test and implement the real metro column mapping, compact ROC period, unpublished budgets, cross-month identity, and source-scoped vector sync.
- [x] Show budget and reporting period separately from award values in the case table; run component test/build.
- [x] Import 52 rows twice; index only metro additions; verify counts and stable IDs.
- [x] Visually inspect procedure PDFs, preserve local sources, index, rerun unchanged sync to verify embedding skip.
- [x] Test a real budget query and two procedure questions with source URL/page citations. Record measurements as smoke checks rather than full evaluation.
- [ ] Review, update source/progress records, commit/push, and verify CI.

Final review found filter-echo matching inside negated clauses and before trailing comparators. Four failing regression cases were added, then fixed with callback clause checks that avoid regex backtracking. Backend: 95 passed. Frontend: 8 passed and production build succeeded.
