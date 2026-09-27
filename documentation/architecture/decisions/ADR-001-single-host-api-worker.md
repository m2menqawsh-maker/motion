# ADR-001: Single-Host Deployment Architecture with Decoupled API and Worker Processes

## Metadata
- **Status:** APPROVED (DEC-01)
- **Date:** 2026-09-27
- **Deciders:** Lead Architect / CTO & Repository Owner
- **Consulted:** S00 Baseline Audit Team
- **Informed:** Core Engineering Team

---

## 1. Context and Problem Statement
The Clean Video Workspace orchestrates video planning, synthesis, and rendering. Video rendering and quality control (QC) are resource-intensive, CPU/GPU-heavy operations requiring Node.js/Remotion and FFmpeg, taking anywhere from tens of seconds to several minutes per render.

In the pre-remediation architecture:
1. Long-running rendering and pipeline operations were executed synchronously inside the FastAPI request loop or via ad-hoc spawned background threads/tasks sharing the same process.
2. Race conditions occurred when concurrent HTTP requests or background threads accessed `.pipeline_state.json` without atomic synchronization (`CONC-001`).
3. An unbounded or crashing render process could degrade or kill the HTTP API process, dropping incoming requests and health checks.
4. Process-local locks (`threading.Lock`, `asyncio.Lock`) were proposed as a quick fix, but process-local locks provide zero protection across separate processes or future multi-worker setups.

We must define the canonical deployment topology for production readiness.

---

## 2. Decision: DEC-01 (APPROVED)

We approve a **Single-host deployment topology with decoupled API and Worker processes**.

```
+-------------------------------------------------------------------------+
|                               HOST MACHINE                              |
|                                                                         |
|  +--------------------+                     +------------------------+  |
|  |   Client / UI      |                     | Durable State / Queue  |  |
|  | (Browser / Agent)  |                     | (SQLite WAL / CAS)     |  |
|  +---------+----------+                     +----+--------------+----+  |
|            | HTTPS                               ^              ^       |
|            v                                     |              |       |
|  +--------------------+                     +----+              |       |
|  |     API Process    |--- (Enqueues Job) --+                   |       |
|  | (FastAPI / Uvicorn)|                                         |       |
|  +--------------------+                                         |       |
|            |                                                    |       |
|            | (Reads / Writes Shared Storage)                    |       |
|            v                                                    v       |
|  +-------------------------------------------------------------------+  |
|  |                     Local Persistent Storage                      |  |
|  |    (/projects, /templates, /assets, /scratch, .pipeline_state)    |  |
|  +-------------------------------------------------------------------+  |
|            ^                                                    ^       |
|            | (Reads / Writes Shared Storage)                    |       |
|            |                                                    |       |
|  +---------+----------+                     +-------------------+----+  |
|  |   Worker Process   |<-- (Leases Job) ----+                        |  |
|  | (Job Execution /   |                                              |  |
|  |  Render / QC)      |                                              |  |
|  +--------------------+                                              |  |
+-------------------------------------------------------------------------+
```

### Key Principles:
1. **Single-Host Boundary:** Both the API process and the Worker process run on the same physical or virtual host. Distributed multi-host clusters (e.g., Kubernetes, Celery with remote brokers, distributed S3/NFS, distributed Consul/Redis locks) are explicitly **out of scope** for this phase.
2. **Process Decoupling:** The API process (FastAPI/Uvicorn) and the Worker process (background pipeline/render executor) run as **separate operating system processes**.
3. **No In-Memory Process-Local Locks for State Coordination:** Because API and Worker are separate processes, in-memory locking (`threading.Lock`, in-memory semaphores) cannot be the source of truth for cross-process state consistency. State coordination must be achieved through durable, cross-process mechanisms (e.g. SQLite in WAL mode with atomic Compare-And-Swap (CAS) or filesystem-level kernel locks `flock`/`fcntl` where applicable).
4. **Shared Local Storage:** Both processes access the same local filesystem storage hierarchy (`projects/`, `templates/`, `assets/`, `scratch/`).
5. **Future-Proof Interfaces:** Core domain interfaces (Job Queue interface, Storage repository interface, State CAS interface) must be designed without process-local assumptions, ensuring future horizontal scaling (multiple workers, remote storage) can be introduced without redesigning domain services.

---

## 3. Rationale and Justification

### Why NOT a Single Monolithic Process?
- Video rendering with Remotion and Chromium consumes significant memory and CPU. A heavy render can easily exhaust node memory or crash. In a single process, this would kill the HTTP API and drop user sessions.
- Decoupling API from Worker ensures the API remains fast, responsive, and able to report progress and accept cancel requests even while heavy rendering is underway.

### Why NOT a Multi-Host Distributed Architecture now?
- A distributed architecture introduces massive operational overhead: network filesystems (NFS latency and POSIX file locking issues), distributed object stores (S3 sync latency for Remotion), distributed job queues (RabbitMQ/Redis), distributed locks (Redis Redlock/Consul), and complex deployment choreography.
- The project's current operational scale and single-node hardware capabilities are fully satisfied by a robust single-host architecture.
- Premature distribution adds latency, failure modes, and debugging friction without business benefit.

---

## 4. Consequences and Constraints

### Positive Consequences
- High responsiveness: API never blocks on render tasks.
- Isolation: Worker crashes or high memory spikes do not bring down the API.
- Simplicity: Operates cleanly on a single host via systemd, supervisord, or docker-compose without distributed dependencies.
- Clear trust boundary between synchronous client interactions and asynchronous execution.

### Negative / Trade-Off Consequences
- Requires an explicit inter-process job queue / lease mechanism (handled in S05/S06).
- Requires cross-process state consistency via durable storage rather than Python in-memory variables.
- File system path confinement must be enforced across both processes.

---

## 5. Implementation Roadmap
- **S01:** Document architecture decisions, trust model, and define process boundary contracts.
- **S02:** Implement security enforcement, path confinement, and command execution policies.
- **S03:** Lifecycle Authority: Establish single authoritative state transition engine and eliminate dual authorities.
- **S04:** Legacy Gate Mutation APIs: Deprecate/transform direct state manipulation endpoints.
- **S05:** State Transactions & CAS: Implement durable SQLite CAS state store, revision control, and inter-process locking/leasing.
- **S06:** Persistent Job Queue and decoupled worker execution loop.
