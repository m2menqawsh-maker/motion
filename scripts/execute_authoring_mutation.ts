#!/usr/bin/env npx tsx
/**
 * scripts/execute_authoring_mutation.ts
 * Production CLI bridge executing Canonical Authoring operations via UnifiedAuthoringSession.
 * S28-R14: Integration of Unified Authoring Subsystem with Production Backend.
 * 
 * Strict Invariants:
 * - ZERO AI vendor SDK imports (OpenAI, Anthropic, Google SDKs forbidden).
 * - ZERO renderer or bundler imports.
 * - Single Canonical VideoDocument authority.
 * - Operates purely in memory on input document, returns updated document + changeset + diagnostics.
 */

import * as fs from "fs";
import {
  type BlueprintV2,
  BlueprintV2Schema,
  type AuthoringRequest,
  type AuthoringResult,
  AuthoringRequestSchema,
  emptyChangeSet,
} from "../contracts";
import {
  UnifiedAuthoringSession,
  instantiateTemplateToCanonicalDocument,
} from "../authoring";

interface BridgeInput {
  action?: "execute_request" | "undo" | "redo" | "instantiate_template";
  document: BlueprintV2;
  request?: AuthoringRequest;
  template_spec?: any;
}

interface BridgeOutput {
  success: boolean;
  base_revision: number;
  result_revision: number;
  blueprint: BlueprintV2;
  changeset: any;
  applied_mutation_ids: string[];
  diagnostics: any[];
  error?: any;
}

async function main(): Promise<void> {
  let rawInput: string;
  const args = process.argv.slice(2);

  if (args.length > 0 && fs.existsSync(args[0])) {
    rawInput = fs.readFileSync(args[0], "utf-8");
  } else {
    // Read from stdin
    const chunks: Buffer[] = [];
    for await (const chunk of process.stdin) {
      chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
    }
    rawInput = Buffer.concat(chunks).toString("utf-8");
  }

  if (!rawInput.trim()) {
    console.error(JSON.stringify({
      success: false,
      error: { code: "EMPTY_INPUT", message: "No input provided to authoring bridge" },
    }));
    process.exit(1);
  }

  let parsedInput: BridgeInput;
  try {
    parsedInput = JSON.parse(rawInput);
  } catch (err: any) {
    console.error(JSON.stringify({
      success: false,
      error: { code: "INVALID_JSON", message: `Malformed JSON input: ${err.message}` },
    }));
    process.exit(1);
  }

  const { action = "execute_request", document, request, template_spec } = parsedInput;

  // Validate document
  const docParse = BlueprintV2Schema.safeParse(document);
  if (!docParse.success) {
    console.log(JSON.stringify({
      success: false,
      base_revision: document?.revision || 0,
      result_revision: document?.revision || 0,
      blueprint: document,
      changeset: emptyChangeSet(),
      applied_mutation_ids: [],
      diagnostics: [{
        code: "AUTHORING_VALIDATION_FAILED",
        message: `Invalid base BlueprintV2: ${docParse.error.message}`,
      }],
      error: { code: "AUTHORING_VALIDATION_FAILED", message: docParse.error.message },
    }));
    process.exit(0);
  }

  const initialBlueprint = docParse.data;
  const session = new UnifiedAuthoringSession(initialBlueprint);

  if (action === "undo") {
    const editor = session.getEditorSession();
    if (!editor.canUndo()) {
      console.log(JSON.stringify({
        success: false,
        base_revision: initialBlueprint.revision || 0,
        result_revision: initialBlueprint.revision || 0,
        blueprint: initialBlueprint,
        changeset: emptyChangeSet(),
        applied_mutation_ids: [],
        diagnostics: [{ code: "NO_UNDO_AVAILABLE", message: "No undo history available" }],
        error: { code: "NO_UNDO_AVAILABLE", message: "No undo history available" },
      }));
      return;
    }
    const undoRes = editor.undo();
    console.log(JSON.stringify({
      success: undoRes.success,
      base_revision: initialBlueprint.revision || 0,
      result_revision: editor.getRevision(),
      blueprint: editor.getBlueprint(),
      changeset: undoRes.changeset,
      applied_mutation_ids: [],
      diagnostics: [],
    }));
    return;
  }

  if (action === "redo") {
    const editor = session.getEditorSession();
    if (!editor.canRedo()) {
      console.log(JSON.stringify({
        success: false,
        base_revision: initialBlueprint.revision || 0,
        result_revision: initialBlueprint.revision || 0,
        blueprint: initialBlueprint,
        changeset: emptyChangeSet(),
        applied_mutation_ids: [],
        diagnostics: [{ code: "NO_REDO_AVAILABLE", message: "No redo history available" }],
        error: { code: "NO_REDO_AVAILABLE", message: "No redo history available" },
      }));
      return;
    }
    const redoRes = editor.redo();
    console.log(JSON.stringify({
      success: redoRes.success,
      base_revision: initialBlueprint.revision || 0,
      result_revision: editor.getRevision(),
      blueprint: editor.getBlueprint(),
      changeset: redoRes.changeset,
      applied_mutation_ids: [],
      diagnostics: [],
    }));
    return;
  }

  if (action === "instantiate_template") {
    try {
      const instantiated = instantiateTemplateToCanonicalDocument(template_spec, {
        projectId: initialBlueprint.project_id,
        fps: initialBlueprint.fps,
        aspectRatio: initialBlueprint.aspect_ratio,
      });
      console.log(JSON.stringify({
        success: true,
        base_revision: initialBlueprint.revision || 0,
        result_revision: (initialBlueprint.revision || 0) + 1,
        blueprint: instantiated,
        changeset: emptyChangeSet(),
        applied_mutation_ids: ["template_instantiation"],
        diagnostics: [],
      }));
    } catch (e: any) {
      console.log(JSON.stringify({
        success: false,
        base_revision: initialBlueprint.revision || 0,
        result_revision: initialBlueprint.revision || 0,
        blueprint: initialBlueprint,
        changeset: emptyChangeSet(),
        applied_mutation_ids: [],
        diagnostics: [{ code: "TEMPLATE_INSTANTIATION_FAILED", message: e.message }],
        error: { code: "TEMPLATE_INSTANTIATION_FAILED", message: e.message },
      }));
    }
    return;
  }

  // Default: executeRequest
  if (!request) {
    console.log(JSON.stringify({
      success: false,
      base_revision: initialBlueprint.revision || 0,
      result_revision: initialBlueprint.revision || 0,
      blueprint: initialBlueprint,
      changeset: emptyChangeSet(),
      applied_mutation_ids: [],
      diagnostics: [{ code: "MISSING_REQUEST", message: "Authoring request is required" }],
      error: { code: "MISSING_REQUEST", message: "Authoring request is required" },
    }));
    return;
  }

  const result: AuthoringResult = session.executeRequest(request);
  console.log(JSON.stringify({
    success: result.success,
    base_revision: result.base_revision,
    result_revision: result.result_revision,
    blueprint: result.blueprint,
    changeset: result.changeset,
    applied_mutation_ids: result.applied_mutation_ids,
    diagnostics: result.diagnostics,
    provenance: result.provenance,
    error: result.error,
  }));
}

main().catch((err) => {
  console.error(JSON.stringify({
    success: false,
    error: { code: "INTERNAL_ERROR", message: err.message || String(err) },
  }));
  process.exit(1);
});
