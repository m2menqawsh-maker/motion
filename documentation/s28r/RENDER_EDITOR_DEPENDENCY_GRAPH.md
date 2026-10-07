# Render & Editor Dependency Graph

**Status**: Verified Reality Graph  
**Milestone**: S28-R01  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  

---

## 1. Global System Architecture & Dependency Flow

This diagram captures the **actual reality** of data, code, and execution flow across the system today, clearly distinguishing:
- **CORE DOMAIN** (Engine-neutral business logic and canonical models)
- **AI INTELLIGENCE** (Creative direction, narrative, compilation)
- **REMOTION RUNTIME** (Engine-specific TSX components, hooks, bundler)
- **INFRASTRUCTURE & ORCHESTRATION** (CLI, workers, storage, API)
- **QC & VERIFICATION** (Probe gates, final container validation)

```mermaid
flowchart TD
    %% ==========================================
    %% SUBGRAPHS & NODES
    %% ==========================================
    
    subgraph AI_Intelligence ["1. AI Creative Intelligence (Neutral)"]
        CB[CreativeBrief] --> NP[NarrativePlan]
        NP --> CP[CreativePlan]
        CP --> BC[BlueprintCompiler]
    end

    subgraph Core_Contracts ["2. Core Contracts & Blueprint (Domain)"]
        BC --> BP[05_blueprint.json\nBlueprintV2]
        AM[02_asset_manifest.json\nManifestV2]
        MM[media_map.json]
        PRJ[project.json]
        BRD[brand.json]
        OVR[overrides.json]
        
        BP --> VBP[validate_blueprint.py\nvalidateBlueprintV2]
        AM --> AR[asset-resolver.ts\nAssetResolver]
    end

    subgraph Materializer_Flow ["3. Asset Materializer (Coupled)"]
        VBP --> MAT[scripts/core/materializer.py]
        AM --> MAT
        MAT -->|Staged to| REM_PUB[remotion-app/public/projects/.../generations/...]
        MAT -->|Writes atomic| MM
    end

    subgraph Render_Input_Gate ["4. Single Render Input Gate"]
        BP --> BRI[scripts/core/render_input.py\nbuild_render_input]
        MM --> BRI
        AM --> BRI
        PRJ --> BRI
        BRD --> BRI
        OVR --> BRI
        BRI --> RP_JSON[render_props.json]
        RP_JSON --> PRI[contracts/render-input.ts\nparseRenderInput]
        PRI --> MRG[remotion-app/src/merge.ts\nmergeProject]
    end

    subgraph Probe_QC_Path ["5. Probe QC & Review Authority"]
        RP_JSON --> PRB[scripts/gates/probe_qc.py\nderive_probe_frame_plan]
        PRB -->|Executes| REM_STILL[npx remotion still\nBlueprintVideo]
        REM_STILL --> PRB_PNG[probe_XX_fYY.png stills]
        PRB_PNG --> CS_PNG[contact_sheet.png]
        CS_PNG --> PRB_REP[probe_qc_report.json + .seal]
        PRB_REP --> RVW_BND[ReviewService\nReviewBundle]
        RVW_BND --> STU_LCK[.studio_unlocked]
    end

    subgraph Preview_Studio_Path ["6. Preview / Studio Path"]
        STU_LCK --> STU_PY[scripts/open_studio.py]
        RP_JSON --> STU_PY
        STU_PY -->|Runs Webpack Dev Server| REM_STU[npx remotion studio\nlocalhost:3000]
        REM_STU -.->|Human Review Inspection| REV_APP[.studio_approved]
    end

    subgraph Render_Execution_Path ["7. Render Execution (Local / Docker)"]
        REV_APP --> ASSERT_AUTH[assert_render_authorized\ngate_3 approval]
        ASSERT_AUTH --> RND_PY[scripts/render_project.py]
        RP_JSON --> RND_PY
        
        RND_PY -->|Local Subprocess| REM_LOC[npx remotion render\nsrc/index.ts BlueprintVideo]
        RND_PY -->|Docker Subprocess| REM_DOC[docker run clean-video-builder\nnpx remotion render]
        
        REM_LOC --> TMP_MP4[out.attempt-N.tmp.mp4]
        REM_DOC --> TMP_MP4
        TMP_MP4 --> OUT_MP4[out.mp4 final container]
    end

    subgraph Final_QC_Path ["8. Final QC & Acceptance (Neutral)"]
        OUT_MP4 --> FQC[scripts/gates/final_qc.py]
        BP --> FQC
        FQC -->|ffprobe analysis| STRM[Stream / Codec / Audio Analysis]
        STRM --> AV_SYNC[AV-Sync Drift Check]
        AV_SYNC --> BLK_FRZ[Black / Freeze Frame Detection]
        BLK_FRZ --> FQC_REP[final_qc_report.json\nPASS / FAIL]
    end

    subgraph Worker_Storage ["9. Worker Orchestration & Cloud Storage"]
        API[api/routers/runs.py] --> RR[RunRepository SQLite/Postgres]
        WRK[scripts/core/worker.py] -->|Poll & Atomic CAS Claim| RR
        WRK -->|Executes Subprocess| PIPELINE[scripts/pipeline.py]
        PIPELINE --> FQC_REP
        FQC_REP -->|Upload output artifacts| STOR[scripts/core/storage/\nStorageService S3/Local]
    end

    subgraph Candidate_CREATE ["10. AI Template Candidate Flow"]
        AI_CR[AI Template Authoring] --> CAND_SRC[CandidateComponent.tsx]
        CAND_SRC --> CAND_RUN[candidate_runtime_runner.py]
        CAND_RUN --> CAND_HARN[CandidateHarness.tsx\nregisterRoot + Composition]
        CAND_HARN --> CAND_STILL[remotion still smoke]
        CAND_STILL --> CAND_GATES[candidate_qc_gate.py]
        CAND_GATES --> PROMOTE[promotion_service.py]
        PROMOTE --> TPL_REG[registry/template-registry.tsx\nCOMPONENT_BINDINGS]
    end

    %% ==========================================
    %% COLOR SCHEMES & STYLES
    %% ==========================================
    classDef aiClass fill:#1a365d,stroke:#2b6cb0,stroke-width:2px,color:#fff;
    classDef coreClass fill:#1c4532,stroke:#2f855a,stroke-width:2px,color:#fff;
    classDef remotionClass fill:#742a2a,stroke:#c53030,stroke-width:2px,color:#fff;
    classDef infraClass fill:#2d3748,stroke:#4a5568,stroke-width:2px,color:#fff;
    classDef qcClass fill:#744210,stroke:#d69e2e,stroke-width:2px,color:#fff;

    class CB,NP,CP,BC,AI_CR aiClass;
    class BP,AM,MM,PRJ,BRD,OVR,VBP,AR,BRI,RP_JSON,PRI,MRG coreClass;
    class MAT,REM_PUB,REM_STILL,REM_STU,REM_LOC,REM_DOC,CAND_HARN,CAND_STILL,TPL_REG remotionClass;
    class STU_PY,RND_PY,API,RR,WRK,PIPELINE,STOR,PROMOTE infraClass;
    class PRB,PRB_PNG,CS_PNG,PRB_REP,RVW_BND,STU_LCK,REV_APP,ASSERT_AUTH,FQC,STRM,AV_SYNC,BLK_FRZ,FQC_REP,CAND_GATES qcClass;
```

---

## 2. Dependency Inversions & Architecture Leaks

Detailed inspection of the repository reveals three architectural inversion loops where high-level or neutral layers depend on lower-level runtime implementation:

```mermaid
flowchart LR
    subgraph Inversion_1 ["Leak 1: Contracts to React/Remotion"]
        A[contracts/blueprint.ts] -->|imports| B[registry/effects-runtime.ts]
        B -->|imports| C[templates/effects/engine-bridge.tsx]
        C -->|imports| D[remotion-app/src/engine/*\nReact Components]
    end

    subgraph Inversion_2 ["Leak 2: Contracts to Remotion Math"]
        E[contracts/animations.ts] -->|imports| F[remotion\ninterpolate, spring]
    end

    subgraph Inversion_3 ["Leak 3: Asset Pipeline to Remotion Public"]
        G[scripts/core/materializer.py] -->|hardcoded staging path| H[remotion-app/public/projects/...]
        H -->|required by| I[remotion staticFile]
    end

    classDef leak fill:#78281f,stroke:#e74c3c,stroke-width:2px,color:#fff;
    class A,B,C,D,E,F,G,H,I leak;
```

---

## 3. Boundary Ownership Summary

| Architectural Boundary | Current Boundary Status | Target Future Status (S28-R) |
| :--- | :--- | :--- |
| **CreativePlan $\to$ Blueprint** | **100% Clean** (via `BlueprintCompiler`) | Maintain clean separation |
| **Blueprint $\to$ Contracts** | **Leaked** (`EFFECTS_RUNTIME`, `animations.ts`) | Purify contracts; eliminate React/Remotion imports |
| **Template Identity $\to$ Component** | **Coupled** (`registry.tsx` binds directly to TSX) | Split into Semantic Catalog and Remotion Bindings |
| **Asset Resolution $\to$ Filesystem** | **Coupled** (`remotion-app/public`) | Decouple asset storage; serve via URL or provider |
| **Probe QC $\to$ Render Engine** | **Coupled** (`npx remotion still`) | Wrap behind `VideoRenderer.render_still()` |
| **Render Execution $\to$ Engine** | **Coupled** (`remotion render`) | Wrap behind `RemotionRendererAdapter` |
| **Final QC $\to$ Output Container** | **100% Clean** (`ffprobe` on `out.mp4`) | Maintain as permanent standard |
| **Worker / Storage $\to$ Engine** | **100% Clean** (subprocess & S3 abstraction) | Maintain as permanent standard |
