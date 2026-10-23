# Cryptographic QC Secret Rotation & Invalidation Procedure (QC_HMAC_SALT)

## 1. Security Context & Threat Assessment
- **Historical Exposure:** The file `.agents/secrets/.qc_salt` was committed and tracked in git revision `92cfe7c`.
- **Classification:** In accordance with standard security directives, the historical secret is deemed **COMPROMISED**.
- **Scope of Impact:** The salt was used by `scripts/gates/probe_qc.py` to sign and verify `probe_qc_report.json` via `.seal` files consumed by `ReviewService`.
- **Enforcement Rule:** Under NO circumstances should the old secret be trusted or reused, and under NO circumstances should the new production secret be written to repository files, commit logs, PR descriptions, or reports.

---

## 2. Containment Actions Taken
1. **Git Tracking Removal:** Removed `.agents/secrets/.qc_salt` from the git index (`git rm --cached .agents/secrets/.qc_salt`).
2. **Git Ignore Hardening:** Added `.agents/secrets/` and `.agents/secrets/.qc_salt` to `.gitignore`.
3. **Runtime Zero-Trust Enforcement:**
   - Probe-QC and ReviewService now strictly require the `QC_HMAC_SALT` environment variable.
   - Removed all fallback reads to `.agents/secrets/.qc_salt`.
   - Removed automatic secret generation in `probe_qc.py`.
   - Absence of `QC_HMAC_SALT` results in immediate explicit execution failure (`RuntimeError`).
4. **Cryptographic Algorithm Hardening:**
   - Replaced naive string concatenation hash `hashlib.sha256(data + salt)` with standard `hmac.new(salt, data, hashlib.sha256)`.
   - Enforced constant-time timing-attack-resistant verification using `hmac.compare_digest`.
   - Detects legacy non-HMAC seals and rejects them with an explicit explanatory message advising re-generation.

---

## 3. Step-by-Step Key Rotation Protocol (Production Deployment)

### Step 3.1: Generate a Fresh High-Entropy HMAC Secret
In a secure offline terminal, generate a minimum 256-bit (32 bytes) random secret:
```bash
# Option A: OpenSSL
openssl rand -hex 32

# Option B: Python secrets module
python -c "import secrets; print(secrets.token_hex(32))"
```
*Note: Do NOT store, log, or send this secret over unencrypted communication channels.*

### Step 3.2: Inject Secret into Target Environment
Store the newly generated secret in the production secrets management system:
- **Kubernetes / HashiCorp Vault / AWS Secrets Manager / GCP Secret Manager:**
  Create secret entry `QC_HMAC_SALT`.
- **Container / Systemd Environment:**
  Inject `QC_HMAC_SALT=<NEW_SECRET>` into the runtime environment of the probe worker and API services.

### Step 3.3: Invalidate and Re-seal Existing QC Reports
Because the signing algorithm upgraded from naive SHA-256 concatenation to HMAC-SHA256, previously sealed reports sealed under the compromised key or old format will fail verification:
1. Re-run Probe-QC for active projects needing unlock:
   ```bash
   QC_HMAC_SALT="<NEW_SECRET>" python scripts/gates/probe_qc.py projects/<workspace_id>/<project_id>
   ```
2. Verify that `probe_qc_report.json.seal` contains the HMAC-SHA256 digest.
3. Validate verification passes:
   ```bash
   QC_HMAC_SALT="<NEW_SECRET>" python scripts/gates/probe_qc.py --verify projects/<workspace_id>/<project_id>
   ```

### Step 3.4: Local Developer Environment Cleanup
All developers and CI pipelines must remove any residual local file:
```bash
rm -f .agents/secrets/.qc_salt
```
Local development and automated test suites set `QC_HMAC_SALT` dynamically via test harnesses or local `.env` files (which are git-ignored).
