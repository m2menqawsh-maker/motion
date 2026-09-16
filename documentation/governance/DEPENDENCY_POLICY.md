# Dependency & Supply-Chain Governance

## Overview
Every new dependency introduces potential points of failure, security vulnerabilities, and architectural drift. To maintain a zero-defect environment, all dependencies (Python, Node/npm, binaries like FFmpeg) are strictly governed.

## Policy for Introducing New Dependencies

Before adding any new dependency to `requirements.txt`, `package.json`, or relying on a new system binary, the following criteria must be met and documented in the PR:

1. **Necessity:** Why is it needed? Can an existing dependency achieve the same goal?
2. **Maintenance:** Is the package actively maintained?
3. **Licensing:** Is the license acceptable for this project?
4. **Security:** Are there known CVEs or security issues?
5. **Privilege:** What runtime privileges does this dependency require?
6. **Impact:** What is the impact on bundle size, runtime performance, and the CI pipeline?

## Automated Checks
- **Node:** `npm audit` must pass without High/Critical vulnerabilities before merge.
- **Python:** Dependency/security scanning (e.g., `pip-audit` or Dependabot) must be enabled and passing.
- **Lockfiles:** `package-lock.json` and `requirements.txt` (or Poetry/Pipenv lock) must be committed and verified.
- **Major Upgrades:** Blind automatic major version upgrades are strictly forbidden. All major upgrades require explicit testing and an Architecture impact review if they alter core pipeline mechanics.
