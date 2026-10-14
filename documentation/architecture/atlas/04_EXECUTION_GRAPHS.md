# MOTION Architecture Atlas — Dependency & Execution Graphs

> **Standard:** Authoritative architectural and runtime diagrams constructed strictly from the verified codebase.
> **Diagram Format:** Mermaid syntax adhering to strict renderer compatibility rules (all node labels quoted, standard node naming).

---

## 1. Full System Architecture Map

```mermaid
flowchart TD
    Client["Authenticated Client (HTTP/API)"] -->|HTTPS / HMAC Token| Gateway["API Gateway (FastAPI / api/main.py)"]

    subgraph SecurityShield["Security & Tenancy Boundary"]
        Gateway --> Auth["Authentication & Scoping (api/auth/)"]
        Auth --> PathGuard["Path Jail & Command Policy (scripts/core/security/)"]
    end

    subgraph DomainServices["Application & Domain Services (api/services/)"]
        PathGuard --> ProjSvc["ProjectService (Projects & Workspaces)"]
        PathGuard --> CanonDocSvc["CanonicalDocumentService (State & Blueprints)"]
        PathGuard --> ReviewSvc["ReviewService (Governance & Signatures)"]
        PathGuard --> RunSvc["RunService (Queue & Execution)"]
        PathGuard --> StorageSvc["StorageService (Media & Artifacts)"]
    end

    subgraph CreativeBrain["Creative Intelligence Engine (ai/)"]
        ProjSvc --> AIOrch["AI Orchestration (ai/orchestration/)"]
        AIOrch --> RecipeEngine["Recipe Matcher (18 Production Recipes)"]
        AIOrch --> NarrativePlanner["Narrative Planner & Script Timing"]
        AIOrch --> TasteEngine["Taste & Typographic Constraints"]
        AIOrch --> BlueprintCompiler["Blueprint Compiler (05_blueprint.json)"]
    end

    subgraph ContextKnowledge["Context, Knowledge & Tool Gateway"]
        AIOrch --> ContextAssembler["Context Assembler (ai/context/)"]
        ContextAssembler --> KnowledgeCatalog["Knowledge Catalog (ai/knowledge/)"]
        ContextAssembler --> SkillsRegistry["Skills Registry (ai/skills/)"]
        AIOrch --> ToolGateway["Tool Gateway (ai/tools/gateway.py)"]
        ToolGateway --> CapRouter["Capability Router (TTS, Media, Search)"]
    end

    subgraph DurableRunEngine["Durable Execution & Lease Engine (scripts/core/)"]
        RunSvc --> RunRepo[("Run Repository & State DB")]
        RunRepo --> WorkerPool["Worker Pool (scripts/core/worker.py)"]
        WorkerPool --> LeaseFence["Project Execution Lock & Lease Fencing"]
        LeaseFence --> Pipeline["Pipeline Orchestrator (scripts/pipeline.py)"]
    end

    subgraph RenderingAndQC["Hermetic Rendering & Quality Gates"]
        Pipeline --> ProbeQC["Pre-Render Probe QC & Contact Sheet"]
        ProbeQC --> RemotionEngine["Remotion React Renderer (remotion-app/)"]
        RemotionEngine --> EngineBridge["EngineBridge Audio Sync"]
        RemotionEngine --> FFmpegMux["FFmpeg MP4 Muxer (libx264/aac)"]
        FFmpegMux --> FinalQC["Final QC & ffprobe Certification"]
    end

    subgraph StorageLayer["Durable Content-Addressable Storage"]
        FinalQC --> StoragePool[("Storage Pool & Asset Catalog")]
        StoragePool --> ArtifactDelivery["HTTP Range Streaming (api/routers/artifacts.py)"]
        ArtifactDelivery --> Client
    end
```

---

## 2. HTTP Request Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as Client Application
    participant Middle as Security Middleware
    participant Router as API Router (api/routers/)
    participant Dep as Dependencies (api/dependencies.py)
    participant Svc as Domain Service (api/services/)
    participant DB as Persistence Layer (SQLite / PostgreSQL)

    User->>Middle: HTTP Request (Headers + Body + Authorization)
    Middle->>Middle: Process CORS, Rate Limiting & Audit Context
    Middle->>Router: Forward Request
    Router->>Dep: Resolve get_auth_context()
    Dep->>Dep: Validate HMAC Signature / Bearer Token
    alt Invalid Identity
        Dep-->>User: 401 Unauthorized
    else Valid Identity
        Dep-->>Router: Return AuthContext(tenant_id, workspace_id)
    end

    Router->>Router: Validate Request Body with Pydantic Schema
    alt Malformed Payload
        Router-->>User: 422 Unprocessable Entity
    else Schema Valid
        Router->>Svc: Invoke Domain Operation
        Svc->>DB: Query / Mutate Data (Tenant Scoped)
        alt Concurrency Revision Conflict
            DB-->>Svc: CAS Version Mismatch
            Svc-->>User: 409 Conflict (Revision Mismatch)
        else Commit Success
            DB-->>Svc: Success Response
            Svc-->>Router: Return Domain Model
            Router-->>User: HTTP 200 / 201 / 206 Response
        end
    end
```

---

## 3. AI Planning & Advisory Proposal Generation

```mermaid
flowchart TD
    Brief["CreativeBrief (Topic, Duration, Aspect Ratio, Tone)"] --> IntentParser["Intent Parser & Keyword Extractor"]
    
    subgraph RecipeSelection["Recipe Matching Stage"]
        IntentParser --> RecipeMatcher["Recipe Matcher"]
        RecipeIndex[("18 Production Recipes Catalog")] --> RecipeMatcher
        RecipeMatcher --> SelectedRecipe["Selected Recipe (Scored Match)"]
    end

    subgraph NarrativePlanning["Narrative Structuring Stage"]
        SelectedRecipe --> NarrativePlanner["Narrative Planner"]
        NarrativePlanner --> SceneBudget["Scene Duration & Cut Allocation"]
        SceneBudget --> SpeechAligner["Speech Timing & Words-Per-Second Normalizer"]
    end

    subgraph TasteEnforcement["Taste & Aesthetics Stage"]
        SpeechAligner --> TasteEngine["Taste Engine"]
        TasteEngine --> ColorHarmonizer["Color Contrast & Palette Resolution"]
        TasteEngine --> FontSelector["Typographic Pairing & Hierarchy Rules"]
        TasteEngine --> SFXMatcher["SFX Binding Matrix"]
    end

    subgraph ProposalCompilation["Blueprint Compilation Stage"]
        ColorHarmonizer --> Compiler["Blueprint Compiler"]
        FontSelector --> Compiler
        SFXMatcher --> Compiler
        Compiler --> BlueprintSpec["05_blueprint.json (Pydantic Schema)"]
        BlueprintSpec --> Proposal["CreativeProposal (Advisory Only)"]
    end
```

---

## 4. Context, Knowledge & Capability Tool Gateway

```mermaid
flowchart LR
    subgraph CreativeEngine["Creative Engine"]
        Task["Creative Task"]
    end

    subgraph ContextPlatform["Context & Knowledge Platform"]
        ContextAssembler["Context Assembler"]
        KnowledgeCatalog["Knowledge Catalog (references/)"]
        SkillsCatalog["Skills Registry (.agents/skills/)"]
    end

    subgraph ToolGatewayLayer["Governed Tool Gateway"]
        ToolGateway["Tool Gateway (ai/tools/gateway.py)"]
        AuditLogger["Audit Logger & Circuit Breaker"]
        CapabilityRouter["Capability Router (ai/tools/router.py)"]
    end

    subgraph ExternalProviders["External & Local Providers"]
        TTS["TTS Provider (ElevenLabs / Local Fallback)"]
        Media["Media Search (Pexels / Local Fallback)"]
        SpeechAlign["Speech Alignment (Whisper / Local Fallback)"]
    end

    Task --> ContextAssembler
    KnowledgeCatalog --> ContextAssembler
    SkillsCatalog --> ContextAssembler
    ContextAssembler --> Task

    Task -->|Request Tool/Capability| ToolGateway
    ToolGateway --> AuditLogger
    AuditLogger --> CapabilityRouter
    CapabilityRouter -->|tts| TTS
    CapabilityRouter -->|media_search| Media
    CapabilityRouter -->|alignment| SpeechAlign
```

---

## 5. Review, Governance & Approval State Machine

```mermaid
stateDiagram-v2
    [*] --> DRAFT: Project Created
    
    DRAFT --> PROPOSED: AI Generates Creative Proposal
    PROPOSED --> DRAFT: Proposal Rejected / Expired
    PROPOSED --> REVIEW_PENDING: Apply Proposal (Blueprint Written with CAS)
    
    state REVIEW_PENDING {
        [*] --> GENERATING_PROBE_QC
        GENERATING_PROBE_QC --> AWAITING_HUMAN_DECISION: Probe QC Pass & Contact Sheet Ready
        GENERATING_PROBE_QC --> DEFECT_DETECTED: Audio/Timing Defect
        DEFECT_DETECTED --> REVISE_PLAN: Return to Planning
    }
    
    AWAITING_HUMAN_DECISION --> APPROVED: ReviewDecision(status='APPROVED') + HMAC Signature
    AWAITING_HUMAN_DECISION --> REJECTED: ReviewDecision(status='REJECTED')
    
    APPROVED --> RENDER_QUEUED: Enqueue Durable Run
    RENDER_QUEUED --> RENDERING: Worker Claims Lease & Validates Signature
    
    state RENDERING {
        [*] --> MATERIALIZING_ASSETS
        MATERIALIZING_ASSETS --> EXECUTING_REMOTION
        EXECUTING_REMOTION --> EXECUTING_FINAL_QC
    }
    
    EXECUTING_FINAL_QC --> COMPLETED: Final QC Pass (Codec, Dur, LUFS)
    EXECUTING_FINAL_QC --> FAILED: Final QC Failure (Defect Logged)
    
    COMPLETED --> [*]
    FAILED --> [*]
    REJECTED --> DRAFT
```

---

## 6. Durable Worker Execution & Lease Fencing

```mermaid
sequenceDiagram
    autonumber
    participant Client as API Router
    participant DB as SQL Run Repository
    participant Worker as Background Worker
    participant Lock as ProjectExecutionLock
    participant Pipe as Pipeline Orchestrator

    Client->>DB: Enqueue Run (project_id, idempotency_key)
    DB-->>Client: Run status = QUEUED
    
    loop Worker Polling Loop
        Worker->>DB: Query next QUEUED run
        alt Run Found
            Worker->>DB: Claim Run (status = CLAIMED, worker_id)
            Worker->>Lock: Acquire exclusive lease on project_id
            alt Lock Acquisition Succeeded
                Worker->>Worker: Spawn background lease heartbeat thread
                loop Heartbeat Every 10s
                    Worker->>DB: Refresh lease expiration timestamp
                end
                Worker->>Pipe: Execute scripts/pipeline.py
                alt Pipeline Succeeded
                    Worker->>DB: Mark Run COMPLETED & Record Artifact Hash
                else Pipeline Failed
                    Worker->>DB: Mark Run FAILED & Record Error Logs
                end
                Worker->>Lock: Release lease
            else Lock Contention / Already Active
                Worker->>DB: Return Run to QUEUED (Backoff)
            end
        end
    end
```

---

## 7. Rendering & Double-Gate Quality Control

```mermaid
flowchart TD
    StartRender["Start Pipeline Render (scripts/pipeline.py)"] --> ProbeGate["Gate 1: Pre-Render Probe QC (scripts/gates/probe_qc.py)"]
    
    subgraph ProbeChecks["Probe QC Validations"]
        ProbeGate --> CheckAudio["Inspect Audio Files & Normalization (-16 LUFS)"]
        ProbeGate --> CheckTimings["Verify Audio Lengths Match Scene Durations"]
        ProbeGate --> GenSheet["Generate Visual Contact Sheet Image"]
    end
    
    CheckAudio & CheckTimings & GenSheet --> ProbeDecision{"Probe QC Pass?"}
    ProbeDecision -->|No| AbortPre["Abort Run: Pre-Render Defect Logged"]
    ProbeDecision -->|Yes| MatAssets["Materialize Assets (scripts/generators/materialize_project.py)"]
    
    subgraph RemotionStage["Remotion Execution"]
        MatAssets --> Bundle["Compile Webpack Remotion Bundle"]
        Bundle --> HeadlessChrome["Launch Headless Chromium"]
        HeadlessChrome --> EngineBridge["EngineBridge Synchronizes Audio with Frames"]
        EngineBridge --> FrameRender["Render Frames at 30fps"]
        FrameRender --> FFmpegMux["FFmpeg Encodes H.264 & AAC (+faststart)"]
    end
    
    FFmpegMux --> FinalGate["Gate 2: Post-Render Final QC (scripts/gates/final_qc.py)"]
    
    subgraph FinalChecks["Final QC Validations (ffprobe)"]
        FinalGate --> CodecCheck["Verify Codec (h264) & Pixel Format (yuv420p)"]
        FinalGate --> ResCheck["Verify Resolution (1920x1080) & Exact 30fps"]
        FinalGate --> DurationCheck["Verify Duration Tolerance (within ±0.1s)"]
        FinalGate --> AudioCheck["Verify Audio Loudness & Frequency"]
    end
    
    CodecCheck & ResCheck & DurationCheck & AudioCheck --> FinalDecision{"Final QC Pass?"}
    FinalDecision -->|No| AbortPost["Abort Run: Corrupt Media Detected"]
    FinalDecision -->|Yes| Deliver["Register Artifact in Storage & Mark COMPLETED"]
```

---

## 8. Data Storage & Tenant Isolation

```mermaid
flowchart TD
    subgraph TenantRequest["Tenant-Scoped Request"]
        Req["Request: GET /api/v1/projects/{proj_id}/artifacts/{art_id}/download"]
        AuthCtx["AuthContext: tenant_id='tenant_alpha', workspace_id='ws_alpha'"]
    end

    Req --> AuthCheck["Security Guard (scripts/core/security/)"]
    AuthCtx --> AuthCheck

    subgraph DatabaseIsolation["Relational State Authority"]
        AuthCheck --> DBQuery["Query: SELECT * FROM projects WHERE id=proj_id AND tenant_id='tenant_alpha'"]
        DBQuery --> RowFound{"Row Exists for Tenant?"}
        RowFound -->|No| Reject404["Return HTTP 404 Not Found (Zero Leakage)"]
        RowFound -->|Yes| ArtQuery["Query: SELECT * FROM artifacts WHERE id=art_id AND project_id=proj_id"]
    end

    subgraph FilesystemIsolation["Filesystem Storage Layer"]
        ArtQuery --> PathResolve["Resolve Path: StorageService.resolve_path(storage_key)"]
        PathResolve --> JailCheck["PathSanitizer.assert_in_workspace(resolved_path, tenant_workspace_root)"]
        JailCheck -->|Path Outside Jail| TrapSecurity["Throw SecurityViolationError (Trapped)"]
        JailCheck -->|Path Valid| ReadMedia["Open File Descriptor with Read Lock"]
    end

    subgraph StreamingPipeline["HTTP Range Streaming"]
        ReadMedia --> ParseRange["Parse Range Header (e.g. bytes=0-1048575)"]
        ParseRange --> EmitChunks["Emit HTTP 206 Partial Content Stream"]
        EmitChunks --> Browser["Video Player Plays Smoothly"]
    end
```

---

## 9. Error Propagation, Retries & Safe Recovery

```mermaid
flowchart TD
    ErrorOccurs["Error Condition Occurs During Execution"] --> ClassifyError{"Classify Error Type"}

    ClassifyError -->|Network Timeout on External AI| AIFallback["Circuit Breaker: Fallback to Local Deterministic Planner"]
    AIFallback --> ContinuePlanning["Continue with Baseline Plan"]

    ClassifyError -->|CAS Revision Conflict| CASConflict["Raise 409 Conflict: Inform Client to Reload State"]
    
    ClassifyError -->|Lock Contention on Project| LeaseConflict["Worker Releases Claim with Exponential Backoff"]
    LeaseConflict --> RetryQueue["Re-queue Run for Next Worker Cycle"]

    ClassifyError -->|Worker Hard Crash (SIGKILL)| HeartbeatDies["Lease Heartbeat Ceases"]
    HeartbeatDies --> LeaseExpires["Timed Lease (60s) Expires in SQL Database"]
    LeaseExpires --> OrphanCollector["Reaper Worker Detects Expired Lease"]
    OrphanCollector --> MarkFailed["Mark Stale Run as FAILED (Reason: WORKER_LOST)"]

    ClassifyError -->|Probe QC Audio Failure| BlockRender["Fail Closed: Mark Review as DEFECT_DETECTED"]
    
    ClassifyError -->|Remotion Compilation Error| CaptureTrace["Capture Subprocess STDERR & Traceback"]
    CaptureTrace --> MarkRunFailed["Mark Run FAILED & Surface Diagnostic to Tenant"]

    ClassifyError -->|Final QC Media Defect| QuarantineMedia["Quarantine Corrupt Video & Mark Run FAILED"]
```
