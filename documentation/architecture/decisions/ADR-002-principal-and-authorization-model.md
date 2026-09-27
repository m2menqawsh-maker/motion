# ADR-002: Server-Verified Principal Model and Role-Based Project Authorization

## Metadata
- **Status:** APPROVED (DEC-04)
- **Date:** 2026-09-27
- **Deciders:** Lead Architect / CTO & Repository Owner
- **Consulted:** S00 Baseline Audit Team
- **Informed:** Core Engineering Team

---

## 1. Context and Problem Statement
In the baseline system (`main @ 4b96960` and audited in `S00`):
1. **Unverified Request Identity (`AUTH-001`):** Endpoints such as `POST /gates/{project_id}/approve/{gate}?by=gui` accepted identity blindly from query strings or request bodies (`by: str = "gui"`). An untrusted client could pass any string (e.g. `by="admin"`, `by="ceo"`, `by="reviewer"`) and the system recorded it as verified truth.
2. **Missing Principal Abstraction (`AUTH-002`):** Domain services directly received strings from FastAPI handlers without an authenticated, server-verified identity object.
3. **No Project Scope Isolation (`AUTH-003`):** Any caller could manipulate any project ID simply by passing it in the path (e.g., `/{project_id}/...`), with zero check whether the caller possessed access rights to that specific project.
4. **No Role Separation (`AUTH-004`):** There was no concept of distinct roles (`viewer`, `editor`, `reviewer`, `operator`, `admin`). A viewer could call endpoints to start stages, approve reviews, or trigger renders.
5. **No Independent Reviewer Privilege (`AUTH-005`):** Approval of critical quality gates (e.g., Gate 3 / `.studio_approved`) was not restricted to a dedicated `reviewer` role.

---

## 2. Decision: DEC-04 (APPROVED)

We approve a **Server-Verified Principal Model and Role-Based Project Authorization Architecture**.

```
+-------------------------------------------------------------------------+
|                               HTTP REQUEST                              |
|   Headers: Authorization: Bearer <signed_token>                         |
|   Body / Query: { ... } (NO identity fields allowed)                    |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                      AUTHENTICATION MIDDLEWARE                          |
|   1. Extracts credentials (HMAC-SHA256 Signed Bearer Token)             |
|   2. Cryptographically verifies HMAC signature BEFORE trusting claims   |
|   3. Verifies expiration, non-empty identity, roles, and project scopes|
|   4. Instantiates immutable server-verified Principal                   |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                          PRINCIPAL ABSTRACTION                          |
|   - principal_id: "usr_948123"                                          |
|   - principal_type: HUMAN | SERVICE | SYSTEM_WORKER                     |
|   - roles: [VIEWER, REVIEWER]                                           |
|   - project_scopes: {"proj_abc123": [VIEWER, REVIEWER]}                 |
|   - auth_method: "SIGNED_BEARER_TOKEN"                                  |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                       AUTHORIZATION ENFORCER                            |
|   Evaluates: Can Principal X perform Action Y on Project Z?             |
|   - If Unauthorized -> 403 Forbidden                                    |
|   - If Project Not in Scope -> 403 Forbidden                            |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                           DOMAIN SERVICE                                |
|   Receives Principal as trusted context.                                |
|   Identity for records/approvals extracted solely from Principal.       |
+------------------------------------+------------------------------------+
```

### Key Principles:
1. **Total Ban on User-Supplied Identity Parameters:**
   - Parameter names such as `approved_by`, `by`, `actor`, `user`, or `reviewer` in request bodies, query strings, or untrusted headers are strictly **rejected** and forbidden as sources of identity.
   - The verified actor ID is derived solely from the server-authenticated `Principal`.
2. **Authentic Credential Architecture (HMAC-SHA256 Signed Tokens):**
   - In S02, production authentication enforces a server-signed bearer token format: `<base64url_payload>.<base64url_hmac_sha256>`.
   - The server verifies HMAC-SHA256 using `AUTH_SECRET_KEY` (configured via `SecuritySettings`, min 32 chars in production) BEFORE parsing or trusting any claim ("Client-provided claims are not trusted claims").
   - Decoupled from transport: domain services receive the abstract `Principal`.
   - Future Provider Replacement: Can be cleanly swapped with an OIDC / OAuth2 identity provider without touching domain services.
3. **Dual Principal Types:**
   - **Human Principal:** Represents a human user (designer, reviewer, admin). Authenticated via server-verified signed bearer tokens.
   - **Service Principal:** Represents an automated component, daemon, or external service. Authenticated via dedicated service credentials.
   - A single shared static API key must NEVER be used to masquerade as an individual human user.
4. **Mandatory Role Hierarchy & Permissions:**
   The authorization model defines at least five canonical roles:
   - `viewer`: Read-only access to project artifacts, status, and render previews.
   - `editor`: Can create projects, edit brand settings, upload assets, and modify blueprints. Cannot approve review gates.
   - `reviewer`: Specifically empowered to approve or reject stage reviews and quality gates. Requires explicit assignment.
   - `operator`: Can trigger pipeline executions, render jobs, and cancellations.
   - `admin`: Full administrative control, system settings, user management, and security audit access.
5. **Project Isolation & Scoping:**
   - Possessing a role (e.g. `editor` or `reviewer`) does not automatically grant that role on all projects.
   - The authorization system must evaluate the tuple: `(Principal, Action, Target Project)`.
   - Access is denied unless the Principal possesses the required permission within the target project's scope (or possesses global `admin` privileges).
6. **Decoupling Domain Services from Transport & Auth Implementation:**
   - Domain services must accept an abstract `Principal` object.
   - Domain logic must have zero dependencies on FastAPI request objects, HTTP headers, cookies, or specific JWT parsing libraries.

---

## 3. Rationale and Justification
- **Defense in Depth:** Deriving identity exclusively from cryptographically verified credentials eliminates spoofing attacks where malicious or accidental requests inject false identity markers.
- **Audit Integrity:** Regulatory compliance, debugging, and review tracking require that the `actor` recorded in state transitions is the actual authenticated entity that triggered the change.
- **Least Privilege:** Separating `editor` from `reviewer` prevents unauthorized self-approvals of unvalidated video blueprints.
- **Provider Independence:** Abstracting `Principal` allows the system to swap or augment authentication providers (e.g., local JWT, Firebase Auth, Okta, Keycloak, internal corporate SSO) without modifying a single line of domain or pipeline logic.

---

## 4. Consequences and Constraints

### Positive Consequences
- Robust protection against impersonation and unauthorized state transitions.
- Multi-tenancy and project isolation ready.
- Clean architectural boundaries: transport layer handles auth; domain layer handles business logic.

### Negative / Trade-Off Consequences
- Calls to API endpoints must now provide valid authentication credentials.
- Test suites must construct mock or testing Principals for testing protected endpoints.
- Slightly higher scaffolding complexity in the API ingress layer.

---

## 5. Implementation Roadmap
- **S01:** Establish data contract, permission matrix, ADRs, settings schema, and RED acceptance tests.
- **S02:** Implement authentication middleware, request dependency injection, and authorization enforcement interceptors.
- **S09:** Implement durable Review Decision Bundle linking verified Reviewer Principal to blueprint and QC hashes.
