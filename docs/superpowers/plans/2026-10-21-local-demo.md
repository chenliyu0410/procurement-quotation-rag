# Local portfolio demonstration

Goal: make the existing persisted local application demonstrable without public deployment.

- [x] Run the ten unchanged evaluation questions against the real configured model, PostgreSQL and Qdrant; save requests, responses, retrieved evidence and timings.
- [x] Inspect the results against source evidence. Record automated checks separately from author review; do not label author/agent review as independent human evaluation. Keep missing relevance labels null.
- [x] Verify the browser query flow and sources page, write a reproducible demonstration script and record any unsupported scenarios honestly.
- [ ] Review the artifacts, commit/push and leave the local application accessible.

Scope: public hosting and additional dated award sources remain outside this local demonstration. Existing main-checkout and push authorization continues. The original ten-question set stays unchanged; successful demonstration queries are a separately named set. No runtime feature changes are planned unless testing reveals a blocking defect.

Ruling: testing found a blocking price-answer flaw, so the minimal deterministic insufficient-sample gate was added with RED-to-GREEN tests for zero/four samples. Existing broad document quality issues are explicitly recorded rather than claimed as passed. Cost: local demonstration is supported, but broad question quality remains below the original target. Homepage examples now match existing verified data.

Verification: backend 97 passed, frontend 8 passed, production build passed with API port8001. Browser budget7 rows and procedure page1/2 links confirmed; source counts confirmed. Live HTTP pricing returned zero qualified samples and null Q1/Q3.

Final review: one Important finding reproduced offline and with a failing regression test: document questions mentioning prices were incorrectly short-circuited. Fixed by retaining generation when document evidence exists. Full backend suite:98 passed. Review verified raw metrics and all citation mappings. Existing document semantics/taxonomy/None display remain documented limitations; public deployment and dated sources remain outside scope.
