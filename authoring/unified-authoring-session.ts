/**
 * authoring/unified-authoring-session.ts — Single Unified Authoring Session Authority.
 * S28-R13: Unified Editor Session over Canonical VideoDocument for AI, User & Templates.
 * 
 * Invariants:
 *   - Both User and AI pass through the EXACT SAME validation, revision checks,
 *     atomic batches, ChangeSet generation, and undo/redo history.
 *   - No AI-only bypass or secondary documents.
 *   - Optimistic concurrency: mismatch on expected_revision returns REVISION_CONFLICT.
 *   - True idempotency: retries with same operation_id return prior result safely.
 *   - Live preview synchronization: updates BrowserPreviewRuntime directly.
 */

import type { BlueprintV2 } from "../contracts/blueprint";
import {
  EditorSession,
  type HistoryEntry,
  type EditorSessionConfig,
} from "../contracts/editor-session";
import {
  type MutationResult,
  type ChangeSet,
  emptyChangeSet,
} from "../contracts/mutations";
import {
  type AuthoringRequest,
  type AuthoringResult,
  type AuthoringDiagnostic,
  type AuthoringProvenance,
  AuthoringRequestSchema,
} from "../contracts/authoring";
import { planAuthoringIntent } from "./intent-planner";
import type { BrowserPreviewRuntime } from "../preview/preview-runtime";

export interface UnifiedAuthoringConfig extends EditorSessionConfig {
  previewRuntime?: BrowserPreviewRuntime;
}

export class UnifiedAuthoringSession {
  private editorSession: EditorSession;
  private operationCache = new Map<string, AuthoringResult>();
  private previewRuntime: BrowserPreviewRuntime | null = null;
  private provenanceHistory: AuthoringProvenance[] = [];

  constructor(initialBlueprint: BlueprintV2, config?: UnifiedAuthoringConfig) {
    this.editorSession = new EditorSession(initialBlueprint, config);
    if (config?.previewRuntime) {
      this.attachPreviewRuntime(config.previewRuntime);
    }
  }

  // ─── Query Accessors ────────────────────────────────────────────────────────

  public getBlueprint(): BlueprintV2 {
    return this.editorSession.getBlueprint();
  }

  public getRevision(): number {
    return this.editorSession.getRevision();
  }

  public getEditorSession(): EditorSession {
    return this.editorSession;
  }

  public canUndo(): boolean {
    return this.editorSession.canUndo();
  }

  public canRedo(): boolean {
    return this.editorSession.canRedo();
  }

  public getProvenanceHistory(): AuthoringProvenance[] {
    return [...this.provenanceHistory];
  }

  public attachPreviewRuntime(previewRuntime: BrowserPreviewRuntime): void {
    this.previewRuntime = previewRuntime;
    // Initial sync
    this.previewRuntime.updateDocument(this.getBlueprint());
  }

  // ─── Unified Authoring Execution (AI & User Common Path) ───────────────────

  /**
   * Authoritative entry point for executing authoring requests from AI, User, or System.
   * Enforces:
   *   1. Schema validation
   *   2. Idempotency deduplication
   *   3. Optimistic concurrency (expected_revision check)
   *   4. Intent planning to typed canonical mutations
   *   5. Atomic execution via EditorSession
   *   6. Preview runtime synchronization
   *   7. Authoring provenance tracking
   */
  public executeRequest(requestInput: unknown): AuthoringResult {
    // 1. Schema Validation
    const parseRes = AuthoringRequestSchema.safeParse(requestInput);
    if (!parseRes.success) {
      const diag: AuthoringDiagnostic = {
        code: "AUTHORING_VALIDATION_FAILED",
        message: `Invalid AuthoringRequest: ${parseRes.error.issues.map((i) => i.message).join("; ")}`,
      };
      return {
        success: false,
        operation_id: (requestInput as any)?.request_id ?? "unknown_op",
        base_revision: this.getRevision(),
        result_revision: this.getRevision(),
        blueprint: this.getBlueprint(),
        changeset: emptyChangeSet(),
        applied_mutation_ids: [],
        idempotent: false,
        diagnostics: [diag],
        error: diag,
      };
    }

    const req = parseRes.data;
    const opKey = req.idempotency_key || req.request_id;

    // 2. Idempotency Check (AI Retry Safety)
    if (this.operationCache.has(opKey)) {
      const cached = this.operationCache.get(opKey)!;
      return {
        ...cached,
        idempotent: true,
      };
    }

    const currentRev = this.getRevision();

    // 3. Optimistic Concurrency Check
    if (req.base_revision !== currentRev) {
      const diag: AuthoringDiagnostic = {
        code: "REVISION_CONFLICT",
        message: `Revision conflict for operation '${req.request_id}': expected revision ${req.base_revision}, but current document is at revision ${currentRev}`,
        details: {
          expected_revision: req.base_revision,
          current_revision: currentRev,
          actor: req.actor,
        },
      };
      return {
        success: false,
        operation_id: req.request_id,
        base_revision: req.base_revision,
        result_revision: currentRev,
        blueprint: this.getBlueprint(),
        changeset: emptyChangeSet(),
        applied_mutation_ids: [],
        idempotent: false,
        diagnostics: [diag],
        error: diag,
      };
    }

    // 4. Intent Planning to Typed Canonical Mutations
    const planRes = planAuthoringIntent(this.getBlueprint(), req);
    if (!planRes.ok) {
      return {
        success: false,
        operation_id: req.request_id,
        base_revision: req.base_revision,
        result_revision: currentRev,
        blueprint: this.getBlueprint(),
        changeset: emptyChangeSet(),
        applied_mutation_ids: [],
        idempotent: false,
        diagnostics: [planRes.error, ...planRes.diagnostics],
        error: planRes.error,
      };
    }

    // 5. Atomic Mutation Application via EditorSession
    let mutResult: MutationResult;

    if (planRes.mutations.length === 1 && !planRes.is_compound) {
      // Single mutation
      mutResult = this.editorSession.applyMutation(planRes.mutations[0], {
        description: req.description ?? planRes.description,
      });
    } else {
      // Atomic compound batch
      mutResult = this.editorSession.applyBatch({
        batch_id: req.request_id,
        author: req.actor,
        mutations: planRes.mutations,
        expected_revision: req.base_revision,
        description: req.description ?? planRes.description,
      });
    }

    if (!mutResult.success) {
      const diag: AuthoringDiagnostic = {
        code: "AUTHORING_VALIDATION_FAILED",
        message: `Mutation application failed: ${mutResult.error?.message ?? "Unknown mutation failure"}`,
        details: { mutation_error: mutResult.error },
      };
      return {
        success: false,
        operation_id: req.request_id,
        base_revision: req.base_revision,
        result_revision: currentRev,
        blueprint: this.getBlueprint(),
        changeset: emptyChangeSet(),
        applied_mutation_ids: [],
        idempotent: false,
        diagnostics: [diag],
        error: diag,
      };
    }

    // 6. Preview Runtime Synchronization
    if (this.previewRuntime) {
      this.previewRuntime.updateDocument(mutResult.blueprint, mutResult.changeset);
    }

    // 7. Authoring Provenance Tracking
    const provenance: AuthoringProvenance = {
      actor_type: req.actor.toUpperCase() as "USER" | "AI" | "SYSTEM",
      operation_id: req.request_id,
      timestamp: Date.now(),
      mutation_ids: mutResult.applied_mutation_ids,
      base_revision: req.base_revision,
      result_revision: mutResult.revision,
      intent_id: req.intent.type,
    };
    this.provenanceHistory.push(provenance);

    // 8. Result Assembly & Cache for Idempotency
    const finalResult: AuthoringResult = {
      success: true,
      operation_id: req.request_id,
      base_revision: req.base_revision,
      result_revision: mutResult.revision,
      blueprint: mutResult.blueprint,
      changeset: mutResult.changeset,
      applied_mutation_ids: mutResult.applied_mutation_ids,
      idempotent: false,
      diagnostics: planRes.diagnostics,
      provenance,
    };

    this.operationCache.set(opKey, finalResult);
    return finalResult;
  }

  // ─── Undo & Redo ────────────────────────────────────────────────────────────

  public undo(): MutationResult {
    const res = this.editorSession.undo();
    if (res.success && this.previewRuntime) {
      this.previewRuntime.updateDocument(res.blueprint, res.changeset);
    }
    return res;
  }

  public redo(): MutationResult {
    const res = this.editorSession.redo();
    if (res.success && this.previewRuntime) {
      this.previewRuntime.updateDocument(res.blueprint, res.changeset);
    }
    return res;
  }
}
