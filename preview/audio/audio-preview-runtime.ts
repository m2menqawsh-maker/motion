/**
 * preview/audio/audio-preview-runtime.ts — Authoritative Audio Preview Runtime.
 * S28-R07: Synchronizes multi-track audio playback with BrowserPreviewRuntime playhead.
 * Single timeline authority: playhead is strictly driven by the canonical video clock.
 * ZERO React or Remotion dependencies.
 */
import type { BlueprintV2 } from "../../contracts/blueprint";
import type { NormalizedVideo } from "../../contracts/normalization";
import { frameToMs, msToFrame } from "../../contracts/timeline";
import { evaluateVideoAtFrame, type EvaluatedAudioTrackState } from "../../contracts/evaluator";
import type { ChangeSet } from "../../contracts/mutations";
import {
  type AudioPreviewState,
  type AudioTrackDescriptor,
  type AudioSyncPolicy,
  type AudioPreviewRuntimeConfig,
  type AudioBufferResolver,
  type AudioPreviewEventMap,
  AudioDiagnosticError,
} from "./audio-types";
import {
  createWebAudioContext,
  MockAudioBuffer,
} from "./web-audio-adapter";

interface ActiveTrackRuntime {
  descriptor: AudioTrackDescriptor;
  gainNode: any;
  sourceNode: any | null;
  buffer: any | null;
  isPlaying: boolean;
  startedAtContextTime: number;
  bufferStartOffsetSec: number;
}

export class AudioPreviewRuntime {
  private context: any;
  private masterGain: any;
  private tracks: Map<string, ActiveTrackRuntime> = new Map();
  private bufferCache: Map<string, any> = new Map();
  private bufferResolver: AudioBufferResolver | null = null;

  private state: AudioPreviewState = "idle";
  private currentFrame: number = 0;
  private fps: number = 30;
  private durationFrames: number = 0;
  private playbackRate: number = 1.0;
  private document: BlueprintV2 | NormalizedVideo | any = null;

  // Synchronization timing
  private playStartContextTime: number = 0;
  private playStartFrame: number = 0;
  private syncPolicy: AudioSyncPolicy;
  private failClosedOnMissingAsset: boolean = false;
  private isDestroyed: boolean = false;

  // Diagnostics & Events
  private diagnostics: AudioDiagnosticError[] = [];
  private listeners: { [K in keyof AudioPreviewEventMap]?: Array<AudioPreviewEventMap[K]> } = {};

  constructor(config?: AudioPreviewRuntimeConfig) {
    this.syncPolicy = {
      maxDriftToleranceMs: config?.syncPolicy?.maxDriftToleranceMs ?? 40,
      hardResyncThresholdMs: config?.syncPolicy?.hardResyncThresholdMs ?? 100,
      syncCheckIntervalMs: config?.syncPolicy?.syncCheckIntervalMs ?? 250,
    };
    this.bufferResolver = config?.bufferResolver ?? null;
    this.failClosedOnMissingAsset = config?.failClosedOnMissingAsset ?? false;

    // Instantiate audio context
    try {
      this.context = createWebAudioContext({
        audioContext: config?.audioContext,
        forceMock: config?.forceMock,
        failClosedIfUnavailable: true,
      });
      this.masterGain = this.context.createGain();
      this.masterGain.connect(this.context.destination);
    } catch (err: any) {
      const diagErr = err instanceof AudioDiagnosticError
        ? err
        : new AudioDiagnosticError("AUDIO_CONTEXT_UNAVAILABLE", err.message);
      this.diagnostics.push(diagErr);
      this.emit("error", diagErr);
      throw diagErr;
    }
  }

  // ─── Playhead Synchronization (Driven by BrowserPreviewRuntime) ─────────────

  public syncPlay(frame: number, playbackRate = 1.0): void {
    if (this.isDestroyed || this.state === "playing") return;

    this.currentFrame = Math.max(0, Math.floor(frame));
    this.playbackRate = playbackRate > 0 ? playbackRate : 1.0;
    this.state = "playing";

    if (this.context.state === "suspended") {
      this.context.resume().catch(() => {});
    }

    this.playStartContextTime = this.context.currentTime;
    this.playStartFrame = this.currentFrame;

    this.startActiveTrackSources();
    this.emit("stateChange", "playing");
  }

  public syncPause(frame: number): void {
    if (this.isDestroyed || this.state === "paused") return;

    this.currentFrame = Math.max(0, Math.floor(frame));
    this.state = "paused";

    this.stopAllTrackSources();
    this.emit("stateChange", "paused");
  }

  public syncSeek(targetFrame: number): void {
    if (this.isDestroyed) return;

    const clamped = Math.max(0, Math.floor(targetFrame));
    this.currentFrame = clamped;

    if (this.state === "playing") {
      this.stopAllTrackSources();
      this.playStartContextTime = this.context.currentTime;
      this.playStartFrame = this.currentFrame;
      this.startActiveTrackSources();
    }
    this.evaluateDucking();
  }

  public syncFrame(frame: number): void {
    if (this.isDestroyed) return;
    this.currentFrame = frame;

    if (this.state === "playing") {
      // 1. Check for tracks that should start or stop at this frame
      this.evaluateTrackBoundariesAtCurrentFrame();

      // 2. Dynamic ducking evaluation
      this.evaluateDucking();

      // 3. Small drift check & correction
      this.checkAndCorrectDrift();
    }
  }

  public syncPlaybackRate(rate: number): void {
    if (rate <= 0) return;
    this.playbackRate = rate;

    for (const track of this.tracks.values()) {
      if (track.sourceNode && track.sourceNode.isPlaying) {
        if (track.sourceNode.playbackRate) {
          track.sourceNode.playbackRate.value = rate;
        }
      }
    }
  }

  // ─── Document Ingestion & Mutation Sync ─────────────────────────────────────

  public syncDocument(
    doc: BlueprintV2 | NormalizedVideo | any,
    changeSet?: ChangeSet
  ): void {
    if (this.isDestroyed) return;
    this.document = doc;
    this.fps = doc.fps ?? 30;

    // Fast partial update path for volume / mute mutations
    const inv = changeSet?.invalidation;
    if (inv && inv.requires_audio_remix && !inv.requires_timeline_rebuild) {
      this.applyPartialVolumeMuteUpdates();
      return;
    }

    // Full graph synchronization
    this.rebuildTrackGraph();

    if (this.state === "playing") {
      this.stopAllTrackSources();
      this.playStartContextTime = this.context.currentTime;
      this.playStartFrame = this.currentFrame;
      this.startActiveTrackSources();
    }
  }

  // ─── Track Graph & Mixing ───────────────────────────────────────────────────

  private rebuildTrackGraph(): void {
    if (!this.document) return;

    const evaluated = evaluateVideoAtFrame(this.document, this.currentFrame);
    const evalTracks = evaluated.audio?.tracks ?? [];

    const currentTrackIds = new Set<string>();

    for (const et of evalTracks) {
      currentTrackIds.add(et.track_id);
      const existing = this.tracks.get(et.track_id);

      const desc: AudioTrackDescriptor = {
        track_id: et.track_id,
        asset_ref: et.asset_ref ?? et.track_id,
        kind: et.kind ?? "sfx",
        startFrame: et.startFrame ?? 0,
        durationFrames: et.durationFrames,
        volume: et.base_volume ?? et.volume,
        muted: et.muted,
        loop: et.kind === "music" ? (this.document.audio?.music?.loop ?? true) : false,
        ducking: et.kind === "music" ? this.document.audio?.music?.ducking : undefined,
      };

      if (!existing) {
        // Create GainNode for new track
        const gainNode = this.context.createGain();
        gainNode.gain.value = et.muted ? 0.0 : et.volume;
        gainNode.connect(this.masterGain);

        const runtimeTrack: ActiveTrackRuntime = {
          descriptor: desc,
          gainNode,
          sourceNode: null,
          buffer: this.bufferCache.get(desc.asset_ref) ?? null,
          isPlaying: false,
          startedAtContextTime: 0,
          bufferStartOffsetSec: 0,
        };

        this.tracks.set(et.track_id, runtimeTrack);

        // Resolve buffer if not cached
        if (!runtimeTrack.buffer && this.bufferResolver) {
          this.resolveAndAttachBuffer(runtimeTrack);
        }
      } else {
        // Update descriptor
        existing.descriptor = desc;
        existing.gainNode.gain.value = desc.muted ? 0.0 : desc.volume;
        if (!existing.buffer) {
          existing.buffer = this.bufferCache.get(desc.asset_ref) ?? null;
          if (!existing.buffer && this.bufferResolver) {
            this.resolveAndAttachBuffer(existing);
          }
        }
      }
    }

    // Remove tracks that no longer exist
    for (const [id, track] of this.tracks.entries()) {
      if (!currentTrackIds.has(id)) {
        if (track.sourceNode) {
          try {
            track.sourceNode.stop();
          } catch {}
        }
        track.gainNode.disconnect();
        this.tracks.delete(id);
      }
    }
  }

  private applyPartialVolumeMuteUpdates(): void {
    if (!this.document) return;

    const evaluated = evaluateVideoAtFrame(this.document, this.currentFrame);
    const evalTracks = evaluated.audio?.tracks ?? [];

    for (const et of evalTracks) {
      const track = this.tracks.get(et.track_id);
      if (track) {
        track.descriptor.volume = et.base_volume ?? et.volume;
        track.descriptor.muted = et.muted;
        const targetGain = et.muted ? 0.0 : et.volume;
        track.gainNode.gain.setValueAtTime(targetGain, this.context.currentTime);
        this.emit("volumeChanged", et.track_id, track.descriptor.volume, et.muted);
      }
    }
  }

  // ─── Playback & Node Scheduling ─────────────────────────────────────────────

  private startActiveTrackSources(): void {
    for (const track of this.tracks.values()) {
      this.evaluateAndStartTrack(track);
    }
    this.evaluateDucking();
  }

  private evaluateAndStartTrack(track: ActiveTrackRuntime): void {
    const desc = track.descriptor;
    const startFrame = desc.startFrame ?? 0;
    const durationFrames = desc.durationFrames;
    const endFrame = durationFrames !== undefined ? startFrame + durationFrames : Infinity;

    const isWithinTiming = this.currentFrame >= startFrame && this.currentFrame < endFrame;
    if (!isWithinTiming) {
      return;
    }

    if (!track.buffer) {
      if (this.failClosedOnMissingAsset) {
        const err = new AudioDiagnosticError(
          "MISSING_ASSET",
          `Missing audio buffer for asset '${desc.asset_ref}' on track '${desc.track_id}'`,
          { track_id: desc.track_id, asset_ref: desc.asset_ref }
        );
        this.diagnostics.push(err);
        this.emit("error", err);
        throw err;
      }
      return;
    }

    // Stop previous source if any
    if (track.sourceNode) {
      try {
        track.sourceNode.stop();
      } catch {}
      track.sourceNode.disconnect();
      track.sourceNode = null;
    }

    // Calculate buffer offset in seconds
    const elapsedFrames = this.currentFrame - startFrame;
    const elapsedSec = (elapsedFrames / this.fps);
    const bufferDuration = track.buffer.duration ?? 0;

    let offsetSec = elapsedSec;
    if (desc.loop && bufferDuration > 0) {
      offsetSec = elapsedSec % bufferDuration;
    } else if (bufferDuration > 0 && offsetSec >= bufferDuration) {
      return; // Past buffer duration
    }

    // Calculate remaining duration
    let remainingSec: number | undefined = undefined;
    if (durationFrames !== undefined) {
      const remainingFrames = endFrame - this.currentFrame;
      remainingSec = remainingFrames / this.fps;
    }

    const source = this.context.createBufferSource();
    source.buffer = track.buffer;
    source.loop = Boolean(desc.loop);
    if (source.playbackRate) {
      source.playbackRate.value = this.playbackRate;
    }
    source.connect(track.gainNode);

    source.onended = () => {
      track.isPlaying = false;
      this.emit("trackStopped", desc.track_id);
    };

    source.start(this.context.currentTime, Math.max(0, offsetSec), remainingSec);
    track.sourceNode = source;
    track.isPlaying = true;
    track.startedAtContextTime = this.context.currentTime;
    track.bufferStartOffsetSec = offsetSec;

    this.emit("trackStarted", desc.track_id, offsetSec);
  }

  private stopAllTrackSources(): void {
    for (const track of this.tracks.values()) {
      if (track.sourceNode) {
        try {
          track.sourceNode.stop(this.context.currentTime);
        } catch {}
        track.sourceNode.disconnect();
        track.sourceNode = null;
      }
      track.isPlaying = false;
      this.emit("trackStopped", track.descriptor.track_id);
    }
  }

  private evaluateTrackBoundariesAtCurrentFrame(): void {
    for (const track of this.tracks.values()) {
      const desc = track.descriptor;
      const startFrame = desc.startFrame ?? 0;
      const endFrame = desc.durationFrames !== undefined ? startFrame + desc.durationFrames : Infinity;

      const shouldBePlaying = this.currentFrame >= startFrame && this.currentFrame < endFrame;

      if (shouldBePlaying && !track.isPlaying) {
        this.evaluateAndStartTrack(track);
      } else if (!shouldBePlaying && track.isPlaying) {
        if (track.sourceNode) {
          try {
            track.sourceNode.stop();
          } catch {}
          track.sourceNode.disconnect();
          track.sourceNode = null;
        }
        track.isPlaying = false;
        this.emit("trackStopped", desc.track_id);
      }
    }
  }

  private evaluateDucking(): void {
    const voTrack = this.tracks.get("audio_voiceover");
    const musicTrack = this.tracks.get("audio_music");

    if (!musicTrack || !musicTrack.descriptor.ducking?.enabled) return;

    const voDesc = voTrack?.descriptor;
    const isVoTimingActive = Boolean(
      voDesc &&
      this.currentFrame >= (voDesc.startFrame ?? 0) &&
      (voDesc.durationFrames === undefined || this.currentFrame < (voDesc.startFrame ?? 0) + voDesc.durationFrames)
    );
    const isVoActive = (voTrack?.isPlaying ?? false) || isVoTimingActive;
    const targetGain = musicTrack.descriptor.muted
      ? 0.0
      : isVoActive
      ? musicTrack.descriptor.ducking.ducking_volume
      : musicTrack.descriptor.volume;

    musicTrack.gainNode.gain.setValueAtTime(targetGain, this.context.currentTime);
  }

  private checkAndCorrectDrift(): void {
    const expectedElapsedSec = (this.currentFrame - this.playStartFrame) / (this.fps * this.playbackRate);
    const actualElapsedSec = this.context.currentTime - this.playStartContextTime;
    const driftMs = Math.abs(actualElapsedSec - expectedElapsedSec) * 1000;

    if (driftMs > this.syncPolicy.maxDriftToleranceMs) {
      if (driftMs > this.syncPolicy.hardResyncThresholdMs) {
        // Resync active sources to the canonical playhead
        this.stopAllTrackSources();
        this.playStartContextTime = this.context.currentTime;
        this.playStartFrame = this.currentFrame;
        this.startActiveTrackSources();
      }
      this.emit("driftCorrected", driftMs, this.currentFrame);
    }
  }

  // ─── Buffer Loading & Asset Resolution ──────────────────────────────────────

  public registerAudioBuffer(assetRef: string, buffer: any): void {
    this.bufferCache.set(assetRef, buffer);
    for (const track of this.tracks.values()) {
      if (track.descriptor.asset_ref === assetRef) {
        track.buffer = buffer;
        if (this.state === "playing" && !track.isPlaying) {
          this.evaluateAndStartTrack(track);
        }
      }
    }
  }

  public async loadAudioFromBuffer(
    assetRef: string,
    arrayBuffer: ArrayBuffer
  ): Promise<any> {
    try {
      const decoded = await this.context.decodeAudioData(arrayBuffer);
      this.registerAudioBuffer(assetRef, decoded);
      return decoded;
    } catch (err: any) {
      const diagErr = new AudioDiagnosticError(
        "DECODE_FAILURE",
        `Failed to decode audio asset '${assetRef}': ${err.message}`,
        { asset_ref: assetRef, details: { original: err.message } }
      );
      this.diagnostics.push(diagErr);
      this.emit("error", diagErr);
      throw diagErr;
    }
  }

  private async resolveAndAttachBuffer(track: ActiveTrackRuntime): Promise<void> {
    if (!this.bufferResolver) return;

    try {
      const res = await this.bufferResolver(track.descriptor.asset_ref);
      if (!res) {
        if (this.failClosedOnMissingAsset) {
          const err = new AudioDiagnosticError(
            "MISSING_ASSET",
            `Resolver returned null for asset '${track.descriptor.asset_ref}'`,
            { asset_ref: track.descriptor.asset_ref, track_id: track.descriptor.track_id }
          );
          this.diagnostics.push(err);
          this.emit("error", err);
        }
        return;
      }

      if (res instanceof ArrayBuffer) {
        await this.loadAudioFromBuffer(track.descriptor.asset_ref, res);
      } else {
        this.registerAudioBuffer(track.descriptor.asset_ref, res);
      }
    } catch (err: any) {
      const diagErr = err instanceof AudioDiagnosticError
        ? err
        : new AudioDiagnosticError(
            "DECODE_FAILURE",
            `Failed to resolve audio buffer: ${err.message}`,
            { asset_ref: track.descriptor.asset_ref }
          );
      this.diagnostics.push(diagErr);
      this.emit("error", diagErr);
    }
  }

  // ─── Master Volume & Controls ───────────────────────────────────────────────

  public setMasterVolume(volume: number): void {
    const clamped = Math.max(0, Math.min(1, volume));
    this.masterGain.gain.setValueAtTime(clamped, this.context.currentTime);
  }

  public getMasterVolume(): number {
    return this.masterGain.gain.value;
  }

  public getTrack(trackId: string): ActiveTrackRuntime | undefined {
    return this.tracks.get(trackId);
  }

  public getTrackCount(): number {
    return this.tracks.size;
  }

  public getState(): AudioPreviewState {
    return this.state;
  }

  public getDiagnostics(): AudioDiagnosticError[] {
    return [...this.diagnostics];
  }

  // ─── Event Emitter ──────────────────────────────────────────────────────────

  public on<K extends keyof AudioPreviewEventMap>(
    event: K,
    listener: AudioPreviewEventMap[K]
  ): () => void {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event]!.push(listener);
    return () => this.off(event, listener);
  }

  public off<K extends keyof AudioPreviewEventMap>(
    event: K,
    listener: AudioPreviewEventMap[K]
  ): void {
    const list = this.listeners[event];
    if (list) {
      this.listeners[event] = list.filter((l) => l !== listener) as any;
    }
  }

  private emit<K extends keyof AudioPreviewEventMap>(
    event: K,
    ...args: Parameters<AudioPreviewEventMap[K]>
  ): void {
    const list = this.listeners[event];
    if (list) {
      for (const listener of list) {
        try {
          (listener as any)(...args);
        } catch (e) {
          console.error(`Error in audio preview event listener for '${event}':`, e);
        }
      }
    }
  }

  public destroy(): void {
    this.isDestroyed = true;
    this.stopAllTrackSources();
    try {
      this.masterGain.disconnect();
    } catch {}
    this.tracks.clear();
    this.bufferCache.clear();
    this.listeners = {};
  }
}
