/**
 * contracts/editor-session.ts — Pure Editor Session, Undo/Redo & History Engine.
 * S28-R04 Part 2: Live Editor Session Core over Canonical Mutation Engine.
 * Enforces:
 *   - Zero duplicate video truth (wraps pure BlueprintV2 exclusively)
 *   - Bijective, exact Undo and Redo
 *   - Bounded, configurable history stack
 *   - Transient editing (live gestures/drags) vs committed mutations
 *   - Safe mutation coalescing (gesture token / target / family matching)
 *   - Redo branch invalidation on new branch fork
 *   - Clean persistence / autosave boundary
 * Pure deterministic execution without wall-clock or randomness.
 */
import {
  type BlueprintV2,
  BlueprintV2Schema,
  type BlueprintScene,
  validateBlueprintV2,
} from "./blueprint";
import {
  type CanonicalMutation,
  CanonicalMutationSchema,
  type MutationBatch,
  type MutationResult,
  type MutationError,
  applyMutation,
  applyBatch,
  emptyChangeSet,
  combineChangeSets,
  type ChangeSet,
} from "./mutations";
import { type CanonicalLayer, type Transform } from "./layers";
import { type Keyframe } from "./keyframes";

// ────────────────────────────────────────────────────────────────────────────
// 1. History Entry & Inverse Information
// ────────────────────────────────────────────────────────────────────────────

export interface HistoryChangedEntities {
  scene_ids: string[];
  layer_ids: string[];
  track_ids: string[];
  clip_ids: string[];
  keyframe_ids: string[];
}

export interface HistoryEntry {
  command_id: string;
  description?: string;
  actor: "user" | "ai" | "system";
  gesture_id?: string;
  forward_mutations: CanonicalMutation[];
  inverse_mutations: CanonicalMutation[];
  revision_before: number;
  revision_after: number;
  changed_entities: HistoryChangedEntities;
  snapshot_before: BlueprintV2;
  snapshot_after: BlueprintV2;
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Pure Helper: Deep Clone
// ────────────────────────────────────────────────────────────────────────────

function cloneBlueprint<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj)) as T;
}

function isSameTarget(m1: CanonicalMutation, m2: CanonicalMutation): boolean {
  if (!("target" in m1 && "target" in m2)) return false;
  const t1 = (m1 as { target?: Record<string, string | undefined> }).target;
  const t2 = (m2 as { target?: Record<string, string | undefined> }).target;
  if (!t1 || !t2) return false;
  return (
    t1.scene_id === t2.scene_id &&
    t1.layer_id === t2.layer_id &&
    t1.clip_id === t2.clip_id &&
    t1.track_id === t2.track_id &&
    t1.keyframe_id === t2.keyframe_id
  );
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Pure Helper: Inverse Mutation Computation
// ────────────────────────────────────────────────────────────────────────────

export function computeInverseMutation(
  blueprint: BlueprintV2,
  mutation: CanonicalMutation
): CanonicalMutation[] {
  const invId = `inv_${mutation.mutation_id}`;
  const author = mutation.author ?? "user";

  switch (mutation.type) {
    case "UPDATE_TEXT": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene) return [];

      if (mutation.target.layer_id) {
        const layer = scene.layers?.find((l) => l.layer_id === mutation.target.layer_id);
        if (!layer || layer.kind !== "text") return [];
        return [
          {
            mutation_id: invId,
            type: "UPDATE_TEXT",
            author,
            target: { scene_id: scene.scene_id, layer_id: layer.layer_id },
            payload: {
              text: layer.text,
              typography: layer.typography ? { ...layer.typography } : undefined,
            },
          },
        ];
      } else {
        const oldText = scene.surface?.text ?? "";
        return [
          {
            mutation_id: invId,
            type: "UPDATE_TEXT",
            author,
            target: { scene_id: scene.scene_id },
            payload: { text: oldText },
          },
        ];
      }
    }

    case "UPDATE_TRANSFORM": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene) return [];

      if (mutation.target.layer_id) {
        const layer = scene.layers?.find((l) => l.layer_id === mutation.target.layer_id);
        if (!layer) return [];
        return [
          {
            mutation_id: invId,
            type: "UPDATE_TRANSFORM",
            author,
            target: { scene_id: scene.scene_id, layer_id: layer.layer_id },
            payload: {
              transform: {
                position: { ...layer.transform.position },
                scale: { ...layer.transform.scale },
                rotation: layer.transform.rotation,
                anchor: { ...layer.transform.anchor },
                opacity: layer.transform.opacity,
              },
            },
          },
        ];
      } else {
        const s = scene.surface;
        return [
          {
            mutation_id: invId,
            type: "UPDATE_TRANSFORM",
            author,
            target: { scene_id: scene.scene_id },
            payload: {
              transform: {
                position: s?.position ? { x: s.position.x, y: s.position.y } : undefined,
                scale: s?.scale !== undefined ? { x: s.scale, y: s.scale } : undefined,
                rotation: s?.rotation,
                opacity: s?.opacity,
              },
            },
          },
        ];
      }
    }

    case "ADD_LAYER": {
      return [
        {
          mutation_id: invId,
          type: "REMOVE_LAYER",
          author,
          target: {
            scene_id: mutation.target.scene_id,
            layer_id: mutation.payload.layer.layer_id,
          },
        },
      ];
    }

    case "REMOVE_LAYER": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene || !scene.layers) return [];
      const layer = scene.layers.find((l) => l.layer_id === mutation.target.layer_id);
      if (!layer) return [];
      return [
        {
          mutation_id: invId,
          type: "ADD_LAYER",
          author,
          target: { scene_id: scene.scene_id },
          payload: { layer: cloneBlueprint(layer) },
        },
      ];
    }

    case "DUPLICATE_LAYER": {
      return [
        {
          mutation_id: invId,
          type: "REMOVE_LAYER",
          author,
          target: {
            scene_id: mutation.target.scene_id,
            layer_id: mutation.payload.new_layer_id,
          },
        },
      ];
    }

    case "REORDER_LAYER": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene || !scene.layers) return [];
      const layerIdx = scene.layers.findIndex((l) => l.layer_id === mutation.target.layer_id);
      if (layerIdx < 0) return [];
      const layer = scene.layers[layerIdx];
      const prevNeighbor = layerIdx > 0 ? scene.layers[layerIdx - 1].layer_id : undefined;

      return [
        {
          mutation_id: invId,
          type: "REORDER_LAYER",
          author,
          target: { scene_id: scene.scene_id, layer_id: layer.layer_id },
          payload: {
            relative_to: prevNeighbor,
            position: prevNeighbor ? "after" : "before",
            new_z_index: layer.z_index,
          },
        },
      ];
    }

    case "MOVE_CLIP": {
      const scene = mutation.target.scene_id
        ? blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id)
        : null;
      if (scene) {
        return [
          {
            mutation_id: invId,
            type: "MOVE_CLIP",
            author,
            target: { scene_id: scene.scene_id },
            payload: { new_start_frame: scene.startFrame },
          },
        ];
      }
      return [];
    }

    case "TRIM_CLIP": {
      const scene = mutation.target.scene_id
        ? blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id)
        : null;
      if (scene) {
        return [
          {
            mutation_id: invId,
            type: "TRIM_CLIP",
            author,
            target: { scene_id: scene.scene_id },
            payload: { new_duration_frames: scene.durationFrames },
          },
        ];
      }
      return [];
    }

    case "SPLIT_CLIP": {
      const scene = mutation.target.scene_id
        ? blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id)
        : null;
      if (scene) {
        const newSceneId = mutation.payload.new_scene_id || `${scene.scene_id}_split`;
        return [
          {
            mutation_id: `${invId}_rem`,
            type: "REMOVE_SCENE",
            author,
            target: { scene_id: newSceneId },
          },
          {
            mutation_id: `${invId}_trim`,
            type: "TRIM_CLIP",
            author,
            target: { scene_id: scene.scene_id },
            payload: { new_duration_frames: scene.durationFrames },
          },
        ];
      }
      return [];
    }

    case "SET_KEYFRAME": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      const layer = scene?.layers?.find((l) => l.layer_id === mutation.target.layer_id);
      const kfId = mutation.payload.keyframe.keyframe_id;
      let existingKf: Keyframe | null = null;

      if (layer?.channels) {
        for (const ch of layer.channels) {
          const found = ch.keyframes.find((k) => k.keyframe_id === kfId);
          if (found) {
            existingKf = found;
            break;
          }
        }
      }

      if (existingKf) {
        return [
          {
            mutation_id: invId,
            type: "SET_KEYFRAME",
            author,
            target: { ...mutation.target },
            payload: { keyframe: cloneBlueprint(existingKf) },
          },
        ];
      } else {
        return [
          {
            mutation_id: invId,
            type: "REMOVE_KEYFRAME",
            author,
            target: {
              scene_id: mutation.target.scene_id,
              layer_id: mutation.target.layer_id,
              keyframe_id: kfId,
            },
          },
        ];
      }
    }

    case "UPDATE_KEYFRAME": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      const layer = scene?.layers?.find((l) => l.layer_id === mutation.target.layer_id);
      const kfId = mutation.target.keyframe_id;
      let existingKf: Keyframe | null = null;

      if (layer?.channels) {
        for (const ch of layer.channels) {
          const found = ch.keyframes.find((k) => k.keyframe_id === kfId);
          if (found) {
            existingKf = found;
            break;
          }
        }
      }

      if (!existingKf) return [];
      return [
        {
          mutation_id: invId,
          type: "UPDATE_KEYFRAME",
          author,
          target: { ...mutation.target },
          payload: {
            patch: {
              frame: existingKf.frame,
              value: existingKf.value,
              interpolation: existingKf.interpolation,
              easing: existingKf.easing,
              bezier: existingKf.bezier,
              spring: existingKf.spring,
            },
          },
        },
      ];
    }

    case "REMOVE_KEYFRAME": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      const layer = scene?.layers?.find((l) => l.layer_id === mutation.target.layer_id);
      const kfId = mutation.target.keyframe_id;
      let existingKf: Keyframe | null = null;

      if (layer?.channels) {
        for (const ch of layer.channels) {
          const found = ch.keyframes.find((k) => k.keyframe_id === kfId);
          if (found) {
            existingKf = found;
            break;
          }
        }
      }

      if (!existingKf) return [];
      return [
        {
          mutation_id: invId,
          type: "SET_KEYFRAME",
          author,
          target: {
            scene_id: mutation.target.scene_id,
            layer_id: mutation.target.layer_id,
          },
          payload: { keyframe: cloneBlueprint(existingKf) },
        },
      ];
    }

    case "SET_TRANSITION": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene) return [];
      if (scene.transition) {
        return [
          {
            mutation_id: invId,
            type: "SET_TRANSITION",
            author,
            target: { scene_id: scene.scene_id },
            payload: { transition: cloneBlueprint(scene.transition) },
          },
        ];
      } else {
        return [
          {
            mutation_id: invId,
            type: "REMOVE_TRANSITION",
            author,
            target: { scene_id: scene.scene_id },
          },
        ];
      }
    }

    case "REMOVE_TRANSITION": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene || !scene.transition) return [];
      return [
        {
          mutation_id: invId,
          type: "SET_TRANSITION",
          author,
          target: { scene_id: scene.scene_id },
          payload: { transition: cloneBlueprint(scene.transition) },
        },
      ];
    }

    case "ADD_SCENE": {
      return [
        {
          mutation_id: invId,
          type: "REMOVE_SCENE",
          author,
          target: { scene_id: mutation.payload.scene.scene_id },
        },
      ];
    }

    case "REMOVE_SCENE": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene) return [];
      return [
        {
          mutation_id: invId,
          type: "ADD_SCENE",
          author,
          payload: { scene: cloneBlueprint(scene) },
        },
      ];
    }

    case "DUPLICATE_SCENE": {
      return [
        {
          mutation_id: invId,
          type: "REMOVE_SCENE",
          author,
          target: { scene_id: mutation.payload.new_scene_id },
        },
      ];
    }

    case "REORDER_SCENE": {
      const sceneIdx = blueprint.scenes.findIndex((s) => s.scene_id === mutation.target.scene_id);
      if (sceneIdx < 0) return [];
      const prevNeighbor = sceneIdx > 0 ? blueprint.scenes[sceneIdx - 1].scene_id : undefined;
      return [
        {
          mutation_id: invId,
          type: "REORDER_SCENE",
          author,
          target: { scene_id: mutation.target.scene_id },
          payload: {
            relative_to: prevNeighbor ?? blueprint.scenes[sceneIdx + 1]?.scene_id ?? "",
            position: prevNeighbor ? "after" : "before",
          },
        },
      ];
    }

    case "UPDATE_PROJECT": {
      return [
        {
          mutation_id: invId,
          type: "UPDATE_PROJECT",
          author,
          payload: {
            fps: blueprint.fps,
            aspect_ratio: blueprint.aspect_ratio,
            meta: blueprint.meta ? cloneBlueprint(blueprint.meta) : undefined,
          },
        },
      ];
    }

    case "UPDATE_AUDIO": {
      return [
        {
          mutation_id: invId,
          type: "UPDATE_AUDIO",
          author,
          payload: {
            voiceover: blueprint.audio?.voiceover ? cloneBlueprint(blueprint.audio.voiceover) : undefined,
            music: blueprint.audio?.music ? cloneBlueprint(blueprint.audio.music) : undefined,
            global_sfx: blueprint.audio?.global_sfx ? cloneBlueprint(blueprint.audio.global_sfx) : undefined,
          },
        },
      ];
    }

    case "SET_AUDIO_LEVEL": {
      const p = mutation.payload;
      let prevVolume = 1.0;
      let prevMute = false;

      if (p.track === "voiceover") {
        prevVolume = blueprint.audio?.voiceover?.volume ?? 1.0;
        prevMute = blueprint.audio?.voiceover?.mute ?? false;
      } else if (p.track === "music") {
        prevVolume = blueprint.audio?.music?.volume ?? 0.15;
        prevMute = blueprint.audio?.music?.mute ?? false;
      } else if (p.track === "sfx" && blueprint.audio?.global_sfx) {
        const found = blueprint.audio.global_sfx.find((s) => s.track_id === p.track_id);
        if (found) {
          prevVolume = found.volume ?? 1.0;
          prevMute = found.mute ?? false;
        }
      }

      return [
        {
          mutation_id: invId,
          type: "SET_AUDIO_LEVEL",
          author,
          payload: {
            track: p.track,
            track_id: p.track_id,
            volume: prevVolume,
            mute: prevMute,
          },
        },
      ];
    }

    case "UPDATE_STYLE": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene) return [];

      if (mutation.target.layer_id) {
        const layer = scene.layers?.find((l) => l.layer_id === mutation.target.layer_id);
        if (!layer) return [];
        if (layer.kind === "shape") {
          return [
            {
              mutation_id: invId,
              type: "UPDATE_STYLE",
              author,
              target: { scene_id: scene.scene_id, layer_id: layer.layer_id },
              payload: {
                backgroundColor: layer.fillColor,
                shape: {
                  fillColor: layer.fillColor,
                  strokeColor: layer.strokeColor,
                  strokeWidth: layer.strokeWidth,
                },
              },
            },
          ];
        } else if (layer.kind === "text") {
          return [
            {
              mutation_id: invId,
              type: "UPDATE_STYLE",
              author,
              target: { scene_id: scene.scene_id, layer_id: layer.layer_id },
              payload: {
                color: layer.typography?.fillColor,
              },
            },
          ];
        }
        return [];
      } else {
        return [
          {
            mutation_id: invId,
            type: "UPDATE_STYLE",
            author,
            target: { scene_id: scene.scene_id },
            payload: {
              backgroundColor: scene.surface?.background,
              color: scene.surface?.color,
              surface: scene.surface ? { ...scene.surface } : undefined,
            },
          },
        ];
      }
    }

    case "REPLACE_MEDIA": {
      const scene = blueprint.scenes.find((s) => s.scene_id === mutation.target.scene_id);
      if (!scene) return [];

      if (mutation.target.layer_id) {
        const layer = scene.layers?.find((l) => l.layer_id === mutation.target.layer_id);
        if (!layer || !("asset_ref" in layer)) return [];
        const mediaLayer = layer as { layer_id: string; asset_ref: string };
        return [
          {
            mutation_id: invId,
            type: "REPLACE_MEDIA",
            author,
            target: { scene_id: scene.scene_id, layer_id: layer.layer_id },
            payload: {
              asset_ref: mediaLayer.asset_ref,
            },
          },
        ];
      } else {
        const oldRef = scene.media_refs?.[0] ?? "asset_fallback";
        return [
          {
            mutation_id: invId,
            type: "REPLACE_MEDIA",
            author,
            target: { scene_id: scene.scene_id },
            payload: {
              asset_ref: oldRef,
            },
          },
        ];
      }
    }

    default:
      return [];
  }
}

// ────────────────────────────────────────────────────────────────────────────
// 4. Editor Session Options & State
// ────────────────────────────────────────────────────────────────────────────

export interface EditorSessionConfig {
  maxHistorySize?: number;
  author?: "user" | "ai" | "system";
}

export interface CommitMutationOptions {
  gestureId?: string;
  coalesce?: boolean;
  description?: string;
}

export class EditorSession {
  private currentBlueprint: BlueprintV2;
  private lastSavedRevision: number;
  private undoStack: HistoryEntry[] = [];
  private redoStack: HistoryEntry[] = [];
  private maxHistorySize: number;
  private defaultAuthor: "user" | "ai" | "system";

  // Transient state for ongoing drag / live interactions
  private transientDraft: BlueprintV2 | null = null;
  private activeGestureId: string | null = null;
  private gestureInitialBlueprint: BlueprintV2 | null = null;
  private gestureMutations: CanonicalMutation[] = [];

  constructor(initialBlueprint: BlueprintV2, config?: EditorSessionConfig) {
    this.currentBlueprint = cloneBlueprint(initialBlueprint);
    this.lastSavedRevision = this.currentBlueprint.revision ?? 0;
    this.maxHistorySize = config?.maxHistorySize ?? 100;
    this.defaultAuthor = config?.author ?? "user";
  }

  // ─── Query Accessors ────────────────────────────────────────────────────────

  public getBlueprint(): BlueprintV2 {
    return this.currentBlueprint;
  }

  public getPreviewBlueprint(): BlueprintV2 {
    return this.transientDraft ?? this.currentBlueprint;
  }

  public getRevision(): number {
    return this.currentBlueprint.revision ?? 0;
  }

  public canUndo(): boolean {
    return this.undoStack.length > 0;
  }

  public canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  public getUndoStackSize(): number {
    return this.undoStack.length;
  }

  public getRedoStackSize(): number {
    return this.redoStack.length;
  }

  public isDirty(): boolean {
    return (this.currentBlueprint.revision ?? 0) !== this.lastSavedRevision;
  }

  public markSaved(): void {
    this.lastSavedRevision = this.currentBlueprint.revision ?? 0;
  }

  public clearHistory(): void {
    this.undoStack = [];
    this.redoStack = [];
  }

  public getHistory(): { undo: HistoryEntry[]; redo: HistoryEntry[] } {
    return {
      undo: [...this.undoStack],
      redo: [...this.redoStack],
    };
  }

  // ─── Transient Mutations (Live Interaction / Scrubber / Drag) ───────────────

  /**
   * Applies an uncommitted transient mutation (e.g. active mouse drag).
   * Updates preview state at 60fps without polluting the undo stack.
   */
  public applyTransientMutation(
    mutationInput: CanonicalMutation,
    gestureId: string
  ): { success: boolean; previewBlueprint: BlueprintV2; error?: MutationError } {
    if (!this.activeGestureId || this.activeGestureId !== gestureId) {
      this.activeGestureId = gestureId;
      this.gestureInitialBlueprint = cloneBlueprint(this.currentBlueprint);
      this.gestureMutations = [];
      this.transientDraft = null;
    }

    // Apply transiently on top of current transient draft or initial snapshot
    const base = cloneBlueprint(this.transientDraft ?? this.gestureInitialBlueprint!);
    base.revision = this.gestureInitialBlueprint!.revision;
    const res = applyMutation(base, mutationInput, { skipSemanticValidation: true });

    if (!res.success) {
      return {
        success: false,
        previewBlueprint: this.getPreviewBlueprint(),
        error: res.error,
      };
    }

    this.transientDraft = res.blueprint;

    // Coalesce within gesture if targeting the same entity and operation type
    const lastMut = this.gestureMutations[this.gestureMutations.length - 1];
    if (lastMut && lastMut.type === mutationInput.type && isSameTarget(lastMut, mutationInput)) {
      this.gestureMutations[this.gestureMutations.length - 1] = mutationInput;
    } else {
      this.gestureMutations.push(mutationInput);
    }

    return {
      success: true,
      previewBlueprint: this.transientDraft,
    };
  }

  /**
   * Commits the active transient gesture into an authoritative revision.
   * Produces exactly ONE history entry for the entire drag gesture.
   */
  public commitGesture(gestureId: string, description?: string): MutationResult | null {
    if (!this.activeGestureId || this.activeGestureId !== gestureId || !this.transientDraft) {
      this.cancelGesture(gestureId);
      return null;
    }

    const preSnapshot = cloneBlueprint(this.gestureInitialBlueprint!);
    const postDraft = cloneBlueprint(this.transientDraft);

    // Run semantic validation on final state
    const semanticCheck = validateBlueprintV2(postDraft);
    if (!semanticCheck.ok) {
      this.cancelGesture(gestureId);
      return {
        success: false,
        revision: this.getRevision(),
        blueprint: this.currentBlueprint,
        applied_mutation_ids: [],
        changeset: emptyChangeSet(),
        error: {
          code: "VALIDATION_FAILED",
          message: `Gesture commit validation failed: ${semanticCheck.errors.join("; ")}`,
        },
      };
    }

    const revBefore = this.getRevision();
    const revAfter = revBefore + 1;
    postDraft.revision = revAfter;

    // Collect mutation IDs applied during gesture
    const appliedIds = this.gestureMutations.map((m) => m.mutation_id);
    postDraft.applied_mutations = [
      ...(this.currentBlueprint.applied_mutations ?? []),
      ...appliedIds,
    ];

    // Compute inverse mutations from initial snapshot for the coalesced mutations
    const inverseMuts: CanonicalMutation[] = [];
    for (let i = this.gestureMutations.length - 1; i >= 0; i--) {
      const invs = computeInverseMutation(preSnapshot, this.gestureMutations[i]);
      inverseMuts.push(...invs);
    }

    // Extract changed entities
    const affectedScenes = new Set<string>();
    const affectedLayers = new Set<string>();
    const affectedClips = new Set<string>();
    const affectedKeyframes = new Set<string>();

    for (const m of this.gestureMutations) {
      if ("target" in m && m.target) {
        const t = m.target as Record<string, string | undefined>;
        if (t.scene_id) affectedScenes.add(t.scene_id);
        if (t.layer_id) affectedLayers.add(t.layer_id);
        if (t.clip_id) affectedClips.add(t.clip_id);
        if (t.keyframe_id) affectedKeyframes.add(t.keyframe_id);
      }
    }

    // Record History Entry
    const historyEntry: HistoryEntry = {
      command_id: `cmd_${gestureId}`,
      description: description ?? `Gesture ${gestureId}`,
      actor: this.defaultAuthor,
      gesture_id: gestureId,
      forward_mutations: [...this.gestureMutations],
      inverse_mutations: inverseMuts,
      revision_before: revBefore,
      revision_after: revAfter,
      changed_entities: {
        scene_ids: Array.from(affectedScenes),
        layer_ids: Array.from(affectedLayers),
        track_ids: [],
        clip_ids: Array.from(affectedClips),
        keyframe_ids: Array.from(affectedKeyframes),
      },
      snapshot_before: preSnapshot,
      snapshot_after: cloneBlueprint(postDraft),
    };

    this.pushHistoryEntry(historyEntry);
    this.redoStack = [];

    // Commit state & clear transient
    this.currentBlueprint = postDraft;
    this.transientDraft = null;
    this.activeGestureId = null;
    this.gestureInitialBlueprint = null;
    this.gestureMutations = [];

    return {
      success: true,
      revision: revAfter,
      blueprint: this.currentBlueprint,
      applied_mutation_ids: appliedIds,
      changeset: emptyChangeSet(),
      idempotent: false,
    };
  }

  public cancelGesture(gestureId: string): void {
    if (this.activeGestureId === gestureId) {
      this.transientDraft = null;
      this.activeGestureId = null;
      this.gestureInitialBlueprint = null;
      this.gestureMutations = [];
    }
  }

  // ─── Authoritative Committed Mutations ──────────────────────────────────────

  /**
   * Applies an authoritative committed mutation with optimistic concurrency,
   * redo branch invalidation, and coalescing support.
   */
  public applyMutation(
    mutationInput: unknown,
    options?: CommitMutationOptions
  ): MutationResult {
    const parseRes = CanonicalMutationSchema.safeParse(mutationInput);
    if (!parseRes.success) {
      return {
        success: false,
        revision: this.getRevision(),
        blueprint: this.currentBlueprint,
        applied_mutation_ids: [],
        changeset: emptyChangeSet(),
        error: {
          code: "INVALID_MUTATION",
          message: `Mutation parse failed: ${parseRes.error.issues.map((i) => i.message).join("; ")}`,
        },
      };
    }

    const mutation = parseRes.data;
    const preSnapshot = cloneBlueprint(this.currentBlueprint);
    const inverseMuts = computeInverseMutation(preSnapshot, mutation);

    // Execute through authoritative mutation engine
    const res = applyMutation(this.currentBlueprint, mutation);
    if (!res.success) {
      return res;
    }

    if (res.idempotent) {
      return res;
    }

    // Check Coalescing with topmost undo entry
    const shouldCoalesce = options?.coalesce && this.canCoalesceWithTop(mutation, options.gestureId);

    if (shouldCoalesce) {
      const topEntry = this.undoStack[this.undoStack.length - 1];
      topEntry.forward_mutations = [mutation];
      topEntry.revision_after = res.revision;
      topEntry.snapshot_after = cloneBlueprint(res.blueprint);
      topEntry.inverse_mutations = computeInverseMutation(topEntry.snapshot_before, mutation);
      topEntry.changed_entities = {
        scene_ids: Array.from(new Set([...topEntry.changed_entities.scene_ids, ...res.changeset.affected_scene_ids])),
        layer_ids: Array.from(new Set([...topEntry.changed_entities.layer_ids, ...res.changeset.affected_layer_ids])),
        track_ids: Array.from(new Set([...topEntry.changed_entities.track_ids, ...res.changeset.affected_track_ids])),
        clip_ids: Array.from(new Set([...topEntry.changed_entities.clip_ids, ...res.changeset.affected_clip_ids])),
        keyframe_ids: Array.from(new Set([...topEntry.changed_entities.keyframe_ids, ...res.changeset.affected_keyframe_ids])),
      };
    } else {
      const historyEntry: HistoryEntry = {
        command_id: `cmd_${mutation.mutation_id}`,
        description: options?.description ?? mutation.description,
        actor: mutation.author ?? this.defaultAuthor,
        gesture_id: options?.gestureId,
        forward_mutations: [mutation],
        inverse_mutations: inverseMuts,
        revision_before: preSnapshot.revision ?? 0,
        revision_after: res.revision,
        changed_entities: {
          scene_ids: res.changeset.affected_scene_ids,
          layer_ids: res.changeset.affected_layer_ids,
          track_ids: res.changeset.affected_track_ids,
          clip_ids: res.changeset.affected_clip_ids,
          keyframe_ids: res.changeset.affected_keyframe_ids,
        },
        snapshot_before: preSnapshot,
        snapshot_after: cloneBlueprint(res.blueprint),
      };

      this.pushHistoryEntry(historyEntry);
    }

    // Invalidate redo stack on new committed branch fork
    this.redoStack = [];

    this.currentBlueprint = res.blueprint;
    return res;
  }

  /**
   * Applies an atomic compound batch of mutations with transactional guarantees.
   */
  public applyBatch(batchInput: unknown): MutationResult {
    const preSnapshot = cloneBlueprint(this.currentBlueprint);
    const res = applyBatch(this.currentBlueprint, batchInput);
    if (!res.success) {
      return res;
    }

    if (res.idempotent) {
      return res;
    }

    const parsedBatch = (batchInput as MutationBatch);
    const inverseMuts: CanonicalMutation[] = [];
    if (parsedBatch.mutations) {
      for (let i = parsedBatch.mutations.length - 1; i >= 0; i--) {
        const invs = computeInverseMutation(preSnapshot, parsedBatch.mutations[i]);
        inverseMuts.push(...invs);
      }
    }

    const historyEntry: HistoryEntry = {
      command_id: `batch_${parsedBatch.batch_id ?? "compound"}`,
      description: parsedBatch.description ?? "Compound batch",
      actor: parsedBatch.author ?? this.defaultAuthor,
      forward_mutations: parsedBatch.mutations ? [...parsedBatch.mutations] : [],
      inverse_mutations: inverseMuts,
      revision_before: preSnapshot.revision ?? 0,
      revision_after: res.revision,
      changed_entities: {
        scene_ids: res.changeset.affected_scene_ids,
        layer_ids: res.changeset.affected_layer_ids,
        track_ids: res.changeset.affected_track_ids,
        clip_ids: res.changeset.affected_clip_ids,
        keyframe_ids: res.changeset.affected_keyframe_ids,
      },
      snapshot_before: preSnapshot,
      snapshot_after: cloneBlueprint(res.blueprint),
    };

    this.pushHistoryEntry(historyEntry);
    this.redoStack = [];

    this.currentBlueprint = res.blueprint;
    return res;
  }

  // ─── Undo & Redo ────────────────────────────────────────────────────────────

  /**
   * Undoes the most recent mutation or compound command.
   * Restores the exact prior canonical state cleanly.
   */
  public undo(): MutationResult {
    if (!this.canUndo()) {
      return {
        success: false,
        revision: this.getRevision(),
        blueprint: this.currentBlueprint,
        applied_mutation_ids: [],
        changeset: emptyChangeSet(),
        error: {
          code: "INVALID_MUTATION",
          message: "Undo stack is empty",
        },
      };
    }

    const entry = this.undoStack.pop()!;
    this.redoStack.push(entry);

    // Exact state restoration from snapshot_before
    const restored = cloneBlueprint(entry.snapshot_before);
    this.currentBlueprint = restored;

    return {
      success: true,
      revision: restored.revision ?? entry.revision_before,
      blueprint: restored,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      idempotent: false,
    };
  }

  /**
   * Redoes the most recently undone mutation.
   * Restores the resulting canonical state cleanly.
   */
  public redo(): MutationResult {
    if (!this.canRedo()) {
      return {
        success: false,
        revision: this.getRevision(),
        blueprint: this.currentBlueprint,
        applied_mutation_ids: [],
        changeset: emptyChangeSet(),
        error: {
          code: "INVALID_MUTATION",
          message: "Redo stack is empty",
        },
      };
    }

    const entry = this.redoStack.pop()!;
    this.undoStack.push(entry);

    // Exact state restoration from snapshot_after
    const resulting = cloneBlueprint(entry.snapshot_after);
    this.currentBlueprint = resulting;

    return {
      success: true,
      revision: resulting.revision ?? entry.revision_after,
      blueprint: resulting,
      applied_mutation_ids: [],
      changeset: emptyChangeSet(),
      idempotent: false,
    };
  }

  // ─── Internal History Invariants ────────────────────────────────────────────

  private pushHistoryEntry(entry: HistoryEntry): void {
    this.undoStack.push(entry);
    while (this.undoStack.length > this.maxHistorySize) {
      this.undoStack.shift();
    }
  }

  private canCoalesceWithTop(mutation: CanonicalMutation, gestureId?: string): boolean {
    if (this.undoStack.length === 0) return false;
    const top = this.undoStack[this.undoStack.length - 1];

    const actor = mutation.author ?? this.defaultAuthor;
    if (top.actor !== actor) return false;
    if (top.forward_mutations.length !== 1) return false;

    const topMut = top.forward_mutations[0];
    if (topMut.type !== mutation.type) return false;

    if (!isSameTarget(topMut, mutation)) return false;

    if (gestureId || top.gesture_id) {
      if (gestureId !== top.gesture_id) return false;
    }

    return true;
  }
}
