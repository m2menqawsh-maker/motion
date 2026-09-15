# Official File States

During and after the remediation process, every file in the project must fall into one of the following states:

| State | Meaning |
|---|---|
| `active` | Currently used, healthy, and part of the official architecture. |
| `needs-update` | In use but requires corrections, refactoring, or security patching. |
| `deprecated` | Slated for removal; no longer the preferred method but still present. |
| `quarantined` | Temporarily isolated to observe if breaking changes occur before final deletion. |
| `historical` | Archival purposes only; must not be executed or referenced by active systems. |
| `unknown` | Initial state before assessment. |
