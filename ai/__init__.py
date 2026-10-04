"""
AI & Media Intelligence Platform (`ai/`)
=========================================
S27.0 Architecture Freeze & Bootstrap Package.

Architectural Rule (ADR-004):
The `ai` package is an orchestration and intelligence subsystem.
It operates strictly above the Tool Layer and Domain Services.

Invariants enforced:
1. AI is not Source of Truth.
2. AI is not authorization authority.
3. AI is not lifecycle authority.
4. AI is not QC authority.
5. AI is not filesystem authority.
6. Direct access to raw project filesystem, raw SQL, or template registry is forbidden.
   All system operations MUST pass through Tool Dispatcher / Domain Services.
"""

__version__ = "0.1.0"
