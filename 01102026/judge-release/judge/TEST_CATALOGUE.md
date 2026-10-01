# Judge test catalogue

136 test functions, 436 executed test cases (parametrised).

| Category | Cases | Meaning |
|---|---:|---|
| AUTHN | 23 | Login & token issuance (A07, A04) |
| TOKEN | 37 | Token validation (A07, A08) |
| RBAC | 12 | Role-based access control (A01) |
| OBJECT | 23 | Object-level authZ & data scope (A01) |
| FILTER | 71 | Filtering, sorting & pagination |
| INPUT | 122 | Input validation & injection (A05) |
| WORKFLOW | 30 | Business rules & idempotency (A06) |
| CONFIG | 62 | Security configuration & hardening (A02) |
| LOGGING | 9 | Security logging & alerting (A09) |
| RESILIENCE | 47 | Exceptional conditions & NFRs (A10, NFR) |

## test_01_login.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| AUTHN-01 | AUTHN | Every active seed user receives a bearer token | 7 |
| AUTHN-02 | AUTHN | Token response is JSON with Cache-Control: no-store | 1 |
| AUTHN-03 | AUTHN | Token is an HS256 JWT signed with JWT_SECRET and iss=expense-api | 1 |
| AUTHN-04 | AUTHN | Token lifetime (exp - iat) is at most 15 minutes | 1 |
| AUTHN-05 | AUTHN | Token payload holds only minimal claims (no email, name, password, hash) | 3 |
| AUTHN-06 | AUTHN | Wrong password -> 401 invalid_credentials | 1 |
| AUTHN-07 | AUTHN | Unknown user, wrong password and inactive user get IDENTICAL responses | 1 |
| AUTHN-08 | AUTHN | Disabled account with the correct password -> 401 | 1 |
| AUTHN-09 | AUTHN | 5 consecutive failures lock the account: correct password then fails | 1 |
| AUTHN-10 | AUTHN | A locked account returns the same generic 401 (no 'locked' disclosure) | 1 |
| AUTHN-11 | AUTHN | Locking one account does not affect other users | 1 |
| AUTHN-12 | AUTHN | A successful login resets the consecutive-failure counter | 1 |
| INPUT-01 | INPUT | Invalid login bodies -> 400 validation_error (never 401/500) | 12 |
| INPUT-02 | INPUT | Malformed / non-object JSON -> 400 validation_error | 5 |
| INPUT-03 | INPUT | Non-JSON Content-Type -> 415 unsupported_media_type | 3 |
| INPUT-04 | INPUT | Injection strings in username/password never authenticate or crash | 7 |
| CONFIG-01 | CONFIG | Only POST is allowed on /auth/token (405) | 4 |

## test_02_rate_limit.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| AUTHN-20 | AUTHN | More than LOGIN_RATE_LIMIT_PER_MINUTE attempts from one client -> 429 | 1 |
| AUTHN-21 | AUTHN | 429 response carries a Retry-After header (1-60 seconds) | 1 |
| AUTHN-22 | AUTHN | While throttled even correct credentials get 429 (no token issued) | 1 |

## test_03_token_validation.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| TOKEN-01 | TOKEN | No Authorization header -> 401 not_authenticated + WWW-Authenticate: Bearer | 1 |
| TOKEN-02 | TOKEN | Malformed / wrong-scheme Authorization header -> 401 | 6 |
| TOKEN-03 | TOKEN | A valid token without the 'Bearer' scheme is rejected | 1 |
| TOKEN-04 | TOKEN | A correctly signed token (JWT_SECRET, HS256, iss) is accepted -> 200 | 1 |
| TOKEN-05 | TOKEN | Payload changed (sub -> finance admin) but old signature kept -> 401 | 1 |
| TOKEN-06 | TOKEN | Signature altered by one character -> 401 | 1 |
| TOKEN-07 | TOKEN | Unsigned token (alg=none) -> 401 | 4 |
| TOKEN-08 | TOKEN | Token signed with a different secret -> 401 | 1 |
| TOKEN-09 | TOKEN | Only HS256 is accepted (algorithm pinned server-side) | 2 |
| TOKEN-10 | TOKEN | Expired token (exp 2 minutes ago) -> 401 | 1 |
| TOKEN-11 | TOKEN | Token missing a required claim (exp/iat/sub/iss) -> 401 | 4 |
| TOKEN-12 | TOKEN | Token from another issuer -> 401 | 3 |
| TOKEN-13 | TOKEN | Correctly signed token for a non-existent / malformed subject -> 401 | 6 |
| TOKEN-14 | TOKEN | Correctly signed token for a DISABLED user (dinesh) -> 401 | 1 |
| TOKEN-15 | TOKEN | Token issued in the future (iat = now + 1 h) -> 401 | 1 |
| TOKEN-16 | TOKEN | Tokens are only read from the header, never from the URL | 1 |
| TOKEN-17 | TOKEN | Every token failure returns the same code + message (no oracle) | 1 |
| TOKEN-18 | TOKEN | Decision endpoint: no token -> 401 even for unknown ids / bad bodies | 1 |
| RBAC-01 | RBAC | A 'role: FINANCE_ADMIN' claim in asha's token must NOT widen her access | 1 |

## test_04_authorization.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| RBAC-02 | RBAC | EMPLOYEE calling the decision API -> 403 (own, colleague's, other team's, unknown id) | 4 |
| RBAC-03 | RBAC | AUDITOR can read everything but cannot decide -> 403 | 3 |
| RBAC-04 | RBAC | EMPLOYEE gets 403 even with an invalid id/body (role is checked first) | 1 |
| RBAC-05 | RBAC | FINANCE_ADMIN and AUDITOR list all 30 claims | 2 |
| RBAC-06 | RBAC | After all denied attempts the claims are unchanged | 1 |
| OBJECT-01 | OBJECT | Manager deciding another team's claim -> 404 (existence hidden) | 1 |
| OBJECT-02 | OBJECT | 'Not yours' and 'does not exist' produce identical responses | 1 |
| OBJECT-03 | OBJECT | Skip-level manager (vikram -> asha's claim) -> 404; only the DIRECT manager decides | 1 |
| OBJECT-04 | OBJECT | Manager deciding their OWN claim -> 403 self_approval_forbidden | 1 |
| OBJECT-05 | OBJECT | Finance admin deciding their OWN pending claim -> 403 self_approval_forbidden | 1 |
| OBJECT-06 | OBJECT | Claims targeted by denied requests keep their original status | 1 |
| OBJECT-07 | OBJECT | List returns exactly the caller's scope (own / own + direct reports) | 7 |
| OBJECT-08 | OBJECT | employee_id filter only narrows the caller's scope (200 with 0 items, never others' data) | 6 |
| OBJECT-09 | OBJECT | asha filtering by PENDING_FINANCE sees only her own claim 1026 | 1 |
| OBJECT-10 | OBJECT | List items expose exactly the documented fields (no hashes, emails, internals) | 3 |

## test_05_filtering.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| FILTER-01 | FILTER | No params: page=1, page_size=20, sorted by newest submitted_at, total=30 | 1 |
| FILTER-02 | FILTER | status filter (single and comma-separated list) | 6 |
| FILTER-03 | FILTER | category filter | 6 |
| FILTER-04 | FILTER | from_date / to_date on expense_date, both bounds inclusive | 6 |
| FILTER-05 | FILTER | from_date == to_date == 2026-07-05 returns exactly claims 1002 and 1029 | 1 |
| FILTER-06 | FILTER | min_amount / max_amount in paise, both bounds inclusive | 7 |
| FILTER-07 | FILTER | q = case-insensitive substring match on description | 7 |
| FILTER-08 | FILTER | Wildcards (% _ * regex) and quotes in q are matched LITERALLY | 10 |
| FILTER-09 | FILTER | Multiple filters combine with AND | 5 |
| FILTER-10 | FILTER | All 6 sort keys; ties broken by id ascending | 6 |
| FILTER-11 | FILTER | Walking pages (size 7) returns every claim exactly once, in order | 1 |
| FILTER-12 | FILTER | Page past the end -> 200 with empty items and the real total | 1 |
| FILTER-13 | FILTER | page_size boundaries 1 and 100 are accepted | 2 |
| FILTER-14 | FILTER | A filter matching nothing -> 200, items [], total 0 | 1 |
| FILTER-15 | FILTER | Response shape {items,page,page_size,total} and item field types | 1 |
| FILTER-16 | FILTER | Filters combined with role scope (manager/employee) match the oracle | 5 |
| FILTER-17 | FILTER | Maximum legal values (q=50 chars, page=10000, amount=100000000) -> 200 | 5 |
| INPUT-10 | INPUT | Stored '<script>' text is returned as JSON data, never rendered as HTML | 1 |

## test_06_list_validation.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| INPUT-11 | INPUT | Invalid, unknown or duplicated query parameters -> 400 validation_error | 49 |
| INPUT-12 | INPUT | Validation errors tell the client WHAT was wrong (message mentions the parameter) | 1 |
| INPUT-13 | INPUT | Validation also applies to employees (no bypass by role) | 1 |

## test_07_workflow.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| WF-01 | WORKFLOW | Direct manager approves a claim <= Rs 50,000 -> APPROVED (other fields unchanged) | 1 |
| WF-02 | WORKFLOW | Exactly Rs 50,000 (5,000,000 paise) -> APPROVED by the manager alone | 1 |
| WF-03 | WORKFLOW | One paisa above the threshold -> PENDING_FINANCE | 1 |
| WF-04 | WORKFLOW | Rs 75,000: manager -> PENDING_FINANCE, then finance -> APPROVED | 1 |
| WF-05 | WORKFLOW | Finance rejects a PENDING_FINANCE claim with a comment -> REJECTED | 1 |
| WF-06 | WORKFLOW | Manager rejects a SUBMITTED claim with a comment -> REJECTED | 1 |
| WF-07 | WORKFLOW | Manager may reject a high-value claim outright (no finance step needed) | 1 |
| WF-08 | WORKFLOW | REJECT without a >= 10 character comment -> 400; claim stays SUBMITTED | 4 |
| WF-09 | WORKFLOW | Manager on APPROVED / REJECTED / PENDING_FINANCE claim -> 409 invalid_state | 3 |
| WF-10 | WORKFLOW | Finance on SUBMITTED / APPROVED / REJECTED claim -> 409 invalid_state | 3 |
| WF-11 | WORKFLOW | A decided claim cannot be re-decided with a new key (APPROVED -> REJECT = 409) | 1 |
| WF-12 | WORKFLOW | vikram decides for his direct reports priya (manager) and farah (finance) | 1 |
| WF-13 | WORKFLOW | The list API shows the new status to the claim owner | 1 |
| WF-14 | WORKFLOW | Same Idempotency-Key + same body -> same 200 response, applied once | 1 |
| WF-15 | WORKFLOW | Same key with a different body or claim -> 409 idempotency_conflict | 1 |
| WF-16 | WORKFLOW | Keys are scoped per caller: another user may use the same key string | 1 |
| WF-17 | WORKFLOW | Missing or malformed Idempotency-Key -> 400 (8-64 chars of A-Z a-z 0-9 -) | 7 |

## test_08_decision_validation.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| INPUT-20 | INPUT | Non-positive / non-integer / oversized claim id -> 400 validation_error | 9 |
| INPUT-21 | INPUT | Invalid decision body -> 400 validation_error; claim unchanged | 13 |
| INPUT-22 | INPUT | Unknown/extra fields in the body -> 400 (no mass assignment) | 7 |
| INPUT-23 | INPUT | After all rejected requests claim 1002 is still SUBMITTED with its original amount | 1 |
| INPUT-24 | INPUT | Malformed JSON / non-object / NaN / empty body -> 400 | 8 |
| INPUT-25 | INPUT | Non-JSON Content-Type on the decision API -> 415 | 3 |
| INPUT-26 | INPUT | A 500-character comment is accepted (boundary) | 1 |
| INPUT-27 | INPUT | Unicode comment (Hindi + emoji) within limits is accepted | 1 |

## test_09_config.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| CONFIG-10 | CONFIG | Security headers on every response, success AND error | 9 |
| CONFIG-11 | CONFIG | No X-Powered-By and no version number in the Server header | 9 |
| CONFIG-12 | CONFIG | Preflight from the configured origin is allowed (exact origin, never *) | 1 |
| CONFIG-13 | CONFIG | Other origins (look-alikes, http://, null) get no CORS permission | 4 |
| CONFIG-14 | CONFIG | Unsupported HTTP methods -> 405 method_not_allowed | 8 |
| CONFIG-15 | CONFIG | Unknown routes -> 404 (or 401) with the standard error envelope, nothing exposed | 8 |

## test_10_prod_mode.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| PROD-01 | CONFIG | APP_ENV=prod without JWT_SECRET -> process exits with a non-zero code | 1 |
| PROD-02 | CONFIG | JWT_SECRET shorter than 32 bytes -> refuse to start | 3 |
| PROD-03 | CONFIG | CORS_ALLOWED_ORIGINS=* -> refuse to start | 1 |
| PROD-04 | CONFIG | APP_ENV other than test|prod (e.g. dev) -> refuse to start | 1 |
| PROD-05 | CONFIG | A rejected secret is never echoed into the logs | 1 |
| PROD-06 | CONFIG | A 32-byte secret is accepted and the prod service starts | 1 |
| PROD-07 | CONFIG | Interactive docs / OpenAPI / actuator are NOT served in prod | 9 |
| PROD-08 | CONFIG | Login + list work in prod mode | 1 |
| PROD-09 | CONFIG | APP_ENV unset defaults to prod behaviour (docs hidden) | 1 |

## test_11_logging.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| LOG-01 | LOGGING | Security events are JSON lines with ts, level, event and request_id | 1 |
| LOG-02 | LOGGING | login_success is logged | 1 |
| LOG-03 | LOGGING | login_failed is logged with the username and the request's X-Request-ID | 1 |
| LOG-04 | LOGGING | account_locked is logged when the lockout threshold is hit | 1 |
| LOG-05 | LOGGING | auth_failed is logged for an invalid bearer token | 1 |
| LOG-06 | LOGGING | access_denied is logged for role (403), visibility (404) and self-approval denials | 1 |
| LOG-07 | LOGGING | expense_decided logged once with expense_id, from_status, to_status (replay not re-logged) | 1 |
| LOG-08 | LOGGING | No password (correct or attempted) ever appears in the logs | 1 |
| LOG-09 | LOGGING | No access token, token signature or JWT_SECRET appears in the logs | 1 |

## test_12_resilience.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| RES-01 | RESILIENCE | Hostile JSON on /auth/token -> 4xx envelope, no 5xx, no stack trace | 12 |
| RES-02 | RESILIENCE | Hostile JSON on /decision -> 4xx envelope, no 5xx, no stack trace | 12 |
| RES-03 | RESILIENCE | Hostile query strings -> no 5xx, no stack trace | 10 |
| RES-04 | RESILIENCE | Request body over 16 KB -> 413 payload_too_large | 1 |
| RES-05 | RESILIENCE | Every response carries a generated X-Request-ID when the client sends none | 1 |
| RES-06 | RESILIENCE | A well-formed client X-Request-ID (8-64 of A-Z a-z 0-9 -) is echoed back | 1 |
| RES-07 | RESILIENCE | A malformed X-Request-ID is replaced, never reflected (header injection) | 5 |
| RES-08 | RESILIENCE | 400/401/403/404/405/409/415 all use the same envelope with correlation_id | 1 |
| RES-09 | RESILIENCE | After all the abuse above the service still works normally | 1 |

## test_13_performance.py

| ID | Category | Requirement verified | Cases |
|---|---|---|---:|
| NFR-01 | RESILIENCE | GET /expenses (page_size=100, filters) p95 < 300 ms over 50 calls | 1 |
| NFR-02 | RESILIENCE | POST /decision p95 < 300 ms over 20 calls | 1 |
| NFR-03 | RESILIENCE | Login p95 < 1500 ms (slow hash, but usable) over 8 calls | 1 |
