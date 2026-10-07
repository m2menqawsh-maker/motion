/**
 * preview/audio/audio-types.ts — Browser Audio Preview Runtime Types.
 * S28-R07: Audio preview graph definitions, synchronization policies,
 * asset loading descriptors, and diagnostic error types.
 * ZERO React or Remotion dependencies.
 */
import type { BlueprintV2 } from "../../contracts/blueprint";
import type { NormalizedVideo } from "../../contracts/normalization";
import type { ChangeSet } from "../../contracts/mutations";

export type AudioPreviewState = "idle" | "playing" | "paused";

export type AudioTrackKind = "voiceover" | "music" | "sfx" | "layer";

export interface AudioTrackDescriptor {
  track_id: string;
  asset_ref: string;
  kind: AudioTrackKind;
  startFrame: number;
  durationFrames?: number;
  volume: number; // 0.0 to 1.0
  muted: boolean;
  loop?: boolean;
  ducking?: {
    enabled: boolean;
    ducking_volume: number;
    duck_under: string[];
  };
}

export type AudioBufferResolver = (
  assetRef: string
) => Promise<AudioBuffer | ArrayBuffer | null> | AudioBuffer | ArrayBuffer | null;

export type AudioDiagnosticErrorCode =
  | "MISSING_ASSET"
  | "DECODE_FAILURE"
  | "UNSUPPORTED_CODEC"
  | "CROSS_ORIGIN_RESTRICTION"
  | "AUDIO_CONTEXT_UNAVAILABLE"
  | "INVALID_AUDIO_TIMING"
  | "PLAYBACK_FAILURE";

export class AudioDiagnosticError extends Error {
  public readonly code: AudioDiagnosticErrorCode;
  public readonly track_id?: string;
  public readonly asset_ref?: string;
  public readonly details?: Record<string, any>;

  constructor(
    code: AudioDiagnosticErrorCode,
    message: string,
    options?: { track_id?: string; asset_ref?: string; details?: Record<string, any> }
  ) {
    super(`[AudioDiagnostic:${code}] ${message}`);
    this.name = "AudioDiagnosticError";
    this.code = code;
    this.track_id = options?.track_id;
    this.asset_ref = options?.asset_ref;
    this.details = options?.details;
  }
}

export interface AudioSyncPolicy {
  maxDriftToleranceMs: number; // default: 40ms (~1.2 frames at 30fps)
  hardResyncThresholdMs: number; // default: 100ms
  syncCheckIntervalMs: number; // default: 250ms
}

export interface AudioPreviewRuntimeConfig {
  syncPolicy?: Partial<AudioSyncPolicy>;
  bufferResolver?: AudioBufferResolver;
  audioContext?: any; // Native or mock AudioContext
  forceMock?: boolean;
  failClosedOnMissingAsset?: boolean;
}

export interface AudioPreviewEventMap {
  stateChange: (state: AudioPreviewState) => void;
  trackStarted: (trackId: string, offsetSec: number) => void;
  trackStopped: (trackId: string) => void;
  driftCorrected: (driftMs: number, frame: number) => void;
  volumeChanged: (trackId: string, volume: number, muted: boolean) => void;
  error: (error: AudioDiagnosticError) => void;
}
