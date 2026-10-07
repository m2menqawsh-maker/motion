/**
 * preview/preview-runtime.ts — Engine-Independent Browser Live Preview Runtime.
 * S28-R06: Orchestrates video document playback, seeking, stepping, aspect ratios,
 * and live mutation reactivity directly over the Canonical VideoDocument.
 * ZERO Remotion runtime authority or React dependencies in core engine.
 */
import type { BlueprintV2 } from "../contracts/blueprint";
import type { NormalizedVideo } from "../contracts/normalization";
import { calculateCanonicalDuration, frameToMs, msToFrame } from "../contracts/timeline";
import type { ChangeSet } from "../contracts/mutations";
import { type EditorSession } from "../contracts/editor-session";
import { buildVisualFrame, resolveDimensionsFromAspectRatio } from "./visual-frame";
import { inspectDocumentCapabilities, assertPreviewSupported, UnsupportedPreviewCapabilityError } from "./capabilities";
import { DOMPreviewDriver } from "./dom-driver";
import type {
  PreviewPlaybackState,
  CanvasDimensions,
  AspectRatioString,
  VisualFrame,
  PreviewRuntimeConfig,
  PreviewEventMap,
  UnsupportedCapabilityReport,
} from "./types";
import { type AudioPreviewRuntime } from "./audio/audio-preview-runtime";
import { resolvePreviewFidelity, type PreviewCapabilityAssessment } from "../contracts/preview-fidelity";
import type { PreviewProxyArtifact } from "../contracts/preview-proxy";
import type { PreviewProxyCoordinator } from "./proxy/proxy-coordinator";

export class BrowserPreviewRuntime {
  private document: BlueprintV2 | NormalizedVideo | any;
  private state: PreviewPlaybackState = "idle";
  private audioRuntime: AudioPreviewRuntime | null = null;
  private currentFrame: number = 0;
  private durationFrames: number = 0;
  private fps: number = 30;
  private playbackRate: number = 1.0;
  private loop: boolean = false;
  private failClosedOnUnsupported: boolean = false;

  private dimensions: CanvasDimensions;
  private aspectRatio: AspectRatioString = "16:9";

  private driver: DOMPreviewDriver | null = null;
  private currentVisualFrame: VisualFrame | null = null;

  // Preview Proxy Subsystem Integration (S28-R07B)
  private activeProxies = new Map<string, PreviewProxyArtifact>();
  private proxyCoordinator: PreviewProxyCoordinator | null = null;
  private proxyUnsubscribe: (() => void) | null = null;

  // Clock & animation loop
  private animationFrameId: number | null = null;
  private timerId: any = null;
  private lastTickTime: number = 0;
  private frameAccumulator: number = 0;
  private isDestroyed: boolean = false;

  // Event Listeners
  private listeners: { [K in keyof PreviewEventMap]?: Array<PreviewEventMap[K]> } = {};

  constructor(
    initialDocument: BlueprintV2 | NormalizedVideo | any,
    config?: PreviewRuntimeConfig
  ) {
    this.loop = config?.loop ?? false;
    this.playbackRate = config?.playbackRate ?? 1.0;
    this.failClosedOnUnsupported = config?.failClosedOnUnsupported ?? false;

    this.setDocumentInternal(initialDocument, true);

    this.aspectRatio = this.document.aspect_ratio || "16:9";
    this.dimensions = config?.defaultDimensions || resolveDimensionsFromAspectRatio(this.aspectRatio);

    if (config?.proxyCoordinator) {
      this.attachProxyCoordinator(config.proxyCoordinator);
    }

    // Initial evaluation at frame 0
    this.evaluateAndEmitCurrentFrame();

    if (config?.audioRuntime) {
      this.attachAudioRuntime(config.audioRuntime);
    }

    if (config?.autoplay) {
      this.play();
    }
  }

  public attachAudioRuntime(audioRuntime: AudioPreviewRuntime): void {
    this.audioRuntime = audioRuntime;
    this.audioRuntime.syncDocument(this.document);
    if (this.state === "playing") {
      this.audioRuntime.syncPlay(this.currentFrame, this.playbackRate);
    }
  }

  public getAudioRuntime(): AudioPreviewRuntime | null {
    return this.audioRuntime;
  }

  // ─── Preview Proxy & Fidelity Methods (S28-R07B) ───────────────────────────

  public attachProxyCoordinator(coordinator: PreviewProxyCoordinator): void {
    if (this.proxyUnsubscribe) {
      this.proxyUnsubscribe();
      this.proxyUnsubscribe = null;
    }
    this.proxyCoordinator = coordinator;
    this.proxyUnsubscribe = coordinator.subscribe((job) => {
      if (job.status === "ready" && job.artifact) {
        const docRev = (this.document as any).revision ?? 0;
        if (job.artifact.canonical_revision === docRev) {
          this.applyProxyArtifact(job.artifact);
        }
      }
    });
  }

  public getProxyCoordinator(): PreviewProxyCoordinator | null {
    return this.proxyCoordinator;
  }

  public applyProxyArtifact(artifact: PreviewProxyArtifact): boolean {
    if (this.isDestroyed) return false;
    const docRev = (this.document as any).revision ?? 0;
    // Stale Result Protection: reject artifacts from older revisions
    if (artifact.canonical_revision < docRev) {
      return false;
    }

    if (artifact.entity.sceneId) {
      this.activeProxies.set(artifact.entity.sceneId, artifact);
    }
    if (artifact.entity.layerId) {
      this.activeProxies.set(artifact.entity.layerId, artifact);
    }
    this.activeProxies.set(artifact.id, artifact);

    this.evaluateAndEmitCurrentFrame();
    this.emit("proxyApplied", artifact.id, artifact.entity.sceneId, artifact.entity.layerId);
    return true;
  }

  public getActiveProxies(): PreviewProxyArtifact[] {
    return Array.from(new Set(this.activeProxies.values()));
  }

  public getFidelityAssessment(): PreviewCapabilityAssessment {
    return resolvePreviewFidelity(this.document);
  }

  // ─── Document Authority & Mutation Integration ──────────────────────────────

  /**
   * Returns the current authoritative canonical document held by the runtime.
   */
  public getDocument(): BlueprintV2 | NormalizedVideo | any {
    return this.document;
  }

  /**
   * Receives a mutated canonical video document (from R04 mutations or EditorSession).
   * Intelligently refreshes preview state according to the ChangeSet invalidation metadata.
   */
  public updateDocument(
    newDocument: BlueprintV2 | NormalizedVideo | any,
    changeSet?: ChangeSet
  ): void {
    if (this.isDestroyed) return;

    this.setDocumentInternal(newDocument, false);

    if (this.proxyCoordinator) {
      this.proxyCoordinator.updateCurrentRevision((newDocument as any).revision ?? 0);
    }

    const inv = changeSet?.invalidation;

    // Selective Proxy Invalidation
    if (changeSet) {
      const affectedScenes = new Set(changeSet.affected_scene_ids || []);
      const affectedLayers = new Set(changeSet.affected_layer_ids || []);

      if (inv?.requires_timeline_rebuild) {
        this.activeProxies.clear();
      } else {
        for (const [key, artifact] of Array.from(this.activeProxies.entries())) {
          if (
            (artifact.entity.sceneId && affectedScenes.has(artifact.entity.sceneId)) ||
            (artifact.entity.layerId && affectedLayers.has(artifact.entity.layerId))
          ) {
            this.activeProxies.delete(key);
          }
        }
      }

      if (this.proxyCoordinator) {
        const count = this.proxyCoordinator.invalidateWithChangeSet(changeSet, (newDocument as any).revision);
        this.emit("proxyInvalidated", count);
      }
    }

    // 1. Recompute timeline duration if needed
    if (!inv || inv.requires_timeline_rebuild) {
      this.durationFrames = calculateCanonicalDuration(this.document.scenes ?? []);
      if (this.currentFrame >= this.durationFrames && this.durationFrames > 0) {
        this.currentFrame = Math.max(0, this.durationFrames - 1);
      }
    }

    // 2. Refresh aspect ratio / layout if needed
    if (!inv || inv.requires_layout) {
      if (this.document.aspect_ratio && this.document.aspect_ratio !== this.aspectRatio) {
        this.aspectRatio = this.document.aspect_ratio;
        this.dimensions = resolveDimensionsFromAspectRatio(this.aspectRatio);
        this.emit("resize", this.dimensions, this.aspectRatio);
      }
    }

    // 3. Immediately sync audio runtime if attached
    if (this.audioRuntime) {
      this.audioRuntime.syncDocument(this.document, changeSet);
    }

    // 4. Immediately re-evaluate and render the frame
    this.evaluateAndEmitCurrentFrame();

    const revision = (this.document as any).revision ?? 0;
    this.emit("documentChange", revision, changeSet);
  }

  /**
   * Attaches directly to an R04 EditorSession.
   */
  public attachEditorSession(session: EditorSession): () => void {
    const syncWithSession = () => {
      const draft = session.getPreviewBlueprint();
      this.updateDocument(draft);
    };

    // Initial sync
    syncWithSession();

    // Returns a detachment callback
    return () => {};
  }

  private unsupportedReport: UnsupportedCapabilityReport | null = null;

  public getUnsupportedReport(): UnsupportedCapabilityReport | null {
    return this.unsupportedReport;
  }

  private setDocumentInternal(doc: any, checkFailClosed: boolean): void {
    this.document = doc;
    this.fps = doc.fps ?? 30;
    this.durationFrames = calculateCanonicalDuration(doc.scenes ?? []);

    const report = inspectDocumentCapabilities(this.document);
    this.unsupportedReport = report;
    if (!report.isSupported) {
      this.emit("unsupportedCapability", report);
      if (checkFailClosed && this.failClosedOnUnsupported) {
        throw new UnsupportedPreviewCapabilityError(report);
      }
    }
  }

  // ─── Playback Controls ──────────────────────────────────────────────────────

  public play(): void {
    if (this.isDestroyed || this.state === "playing") return;

    if (this.currentFrame >= this.durationFrames - 1 && this.durationFrames > 0) {
      this.currentFrame = 0;
    }

    this.state = "playing";
    this.lastTickTime = typeof performance !== "undefined" ? performance.now() : Date.now();
    this.frameAccumulator = 0;
    this.startPlaybackLoop();
    this.audioRuntime?.syncPlay(this.currentFrame, this.playbackRate);
    this.emit("play");
  }

  public pause(): void {
    if (this.isDestroyed || this.state === "paused") return;

    this.state = "paused";
    this.stopPlaybackLoop();
    this.audioRuntime?.syncPause(this.currentFrame);
    this.emit("pause");
  }

  public seek(targetFrame: number): void {
    if (this.isDestroyed) return;

    const clamped = Math.max(0, Math.min(Math.floor(targetFrame), Math.max(0, this.durationFrames - 1)));
    this.currentFrame = clamped;
    this.audioRuntime?.syncSeek(this.currentFrame);
    this.evaluateAndEmitCurrentFrame();
    this.emit("seek", this.currentFrame);
  }

  public seekToMs(ms: number): void {
    const frame = msToFrame(ms, this.fps);
    this.seek(frame);
  }

  public stepForward(frames = 1): void {
    this.seek(this.currentFrame + frames);
  }

  public stepBackward(frames = 1): void {
    this.seek(this.currentFrame - frames);
  }

  public setPlaybackRate(rate: number): void {
    if (rate > 0) {
      this.playbackRate = rate;
      this.audioRuntime?.syncPlaybackRate(rate);
    }
  }

  public getPlaybackRate(): number {
    return this.playbackRate;
  }

  // ─── Viewport & Sizing ──────────────────────────────────────────────────────

  public setDimensions(width: number, height: number): void {
    if (width > 0 && height > 0) {
      this.dimensions = { width: Math.round(width), height: Math.round(height) };
      if (this.driver) {
        this.driver.updateViewportScale(this.dimensions);
      }
      this.evaluateAndEmitCurrentFrame();
      this.emit("resize", this.dimensions, this.aspectRatio);
    }
  }

  public setAspectRatio(ratio: AspectRatioString): void {
    this.aspectRatio = ratio;
    this.dimensions = resolveDimensionsFromAspectRatio(ratio);
    if (this.driver) {
      this.driver.updateViewportScale(this.dimensions);
    }
    this.evaluateAndEmitCurrentFrame();
    this.emit("resize", this.dimensions, this.aspectRatio);
  }

  // ─── State Accessors ────────────────────────────────────────────────────────

  public getState(): PreviewPlaybackState {
    return this.state;
  }

  public getCurrentFrame(): number {
    return this.currentFrame;
  }

  public getCurrentTimeMs(): number {
    return frameToMs(this.currentFrame, this.fps);
  }

  public getDurationFrames(): number {
    return this.durationFrames;
  }

  public getDurationMs(): number {
    return frameToMs(this.durationFrames, this.fps);
  }

  public getFps(): number {
    return this.fps;
  }

  public getDimensions(): CanvasDimensions {
    return { ...this.dimensions };
  }

  public getAspectRatio(): string {
    return this.aspectRatio;
  }

  public getCurrentVisualFrame(): VisualFrame | null {
    return this.currentVisualFrame;
  }

  // ─── DOM Mount / Driver Integration ─────────────────────────────────────────

  public mount(container: HTMLElement, options?: { showDiagnosticsOverlay?: boolean }): void {
    if (this.driver) {
      this.driver.destroy();
    }
    this.driver = new DOMPreviewDriver({
      container,
      showDiagnosticsOverlay: options?.showDiagnosticsOverlay ?? true,
    });
    if (this.currentVisualFrame) {
      this.driver.renderFrame(this.currentVisualFrame);
    }
  }

  public unmount(): void {
    if (this.driver) {
      this.driver.destroy();
      this.driver = null;
    }
  }

  public getDriver(): DOMPreviewDriver | null {
    return this.driver;
  }

  // ─── Internal Clock & Evaluation ────────────────────────────────────────────

  private evaluateAndEmitCurrentFrame(): void {
    try {
      const visualFrame = buildVisualFrame(
        this.document,
        this.currentFrame,
        this.dimensions,
        this.activeProxies
      );
      this.currentVisualFrame = visualFrame;

      if (this.driver) {
        this.driver.renderFrame(visualFrame);
      }

      this.emit("frame", visualFrame.frame, visualFrame.timeMs, visualFrame);
    } catch (err: any) {
      this.emit("error", err);
    }
  }

  private startPlaybackLoop(): void {
    this.stopPlaybackLoop();

    const frameDurationMs = 1000 / (this.fps * this.playbackRate);

    const tick = () => {
      if (this.state !== "playing" || this.isDestroyed) return;

      const now = typeof performance !== "undefined" ? performance.now() : Date.now();
      const elapsed = now - this.lastTickTime;
      this.lastTickTime = now;

      this.frameAccumulator += elapsed;

      let advancedFrames = 0;
      while (this.frameAccumulator >= frameDurationMs) {
        this.frameAccumulator -= frameDurationMs;
        advancedFrames++;
      }

      if (advancedFrames > 0) {
        const nextFrame = this.currentFrame + advancedFrames;
        if (nextFrame >= this.durationFrames) {
          if (this.loop) {
            this.currentFrame = nextFrame % Math.max(1, this.durationFrames);
            this.evaluateAndEmitCurrentFrame();
            this.audioRuntime?.syncFrame(this.currentFrame);
          } else {
            this.currentFrame = Math.max(0, this.durationFrames - 1);
            this.state = "paused";
            this.evaluateAndEmitCurrentFrame();
            this.audioRuntime?.syncPause(this.currentFrame);
            this.emit("ended");
            this.emit("pause");
            return;
          }
        } else {
          this.currentFrame = nextFrame;
          this.evaluateAndEmitCurrentFrame();
          this.audioRuntime?.syncFrame(this.currentFrame);
        }
      }

      if (typeof requestAnimationFrame !== "undefined") {
        this.animationFrameId = requestAnimationFrame(tick);
      } else {
        this.timerId = setTimeout(tick, Math.max(1, frameDurationMs - this.frameAccumulator));
      }
    };

    if (typeof requestAnimationFrame !== "undefined") {
      this.animationFrameId = requestAnimationFrame(tick);
    } else {
      this.timerId = setTimeout(tick, frameDurationMs);
    }
  }

  private stopPlaybackLoop(): void {
    if (this.animationFrameId !== null && typeof cancelAnimationFrame !== "undefined") {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    if (this.timerId !== null) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
  }

  // ─── Event Emitter ──────────────────────────────────────────────────────────

  public on<K extends keyof PreviewEventMap>(event: K, listener: PreviewEventMap[K]): () => void {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event]!.push(listener);
    if (event === "unsupportedCapability" && this.unsupportedReport && !this.unsupportedReport.isSupported) {
      try {
        (listener as any)(this.unsupportedReport);
      } catch (e) {
        console.error("Error invoking initial unsupportedCapability listener:", e);
      }
    }
    return () => this.off(event, listener);
  }

  public off<K extends keyof PreviewEventMap>(event: K, listener: PreviewEventMap[K]): void {
    const list = this.listeners[event];
    if (list) {
      this.listeners[event] = list.filter((l) => l !== listener) as any;
    }
  }

  private emit<K extends keyof PreviewEventMap>(event: K, ...args: Parameters<PreviewEventMap[K]>): void {
    const list = this.listeners[event];
    if (list) {
      for (const listener of list) {
        try {
          (listener as any)(...args);
        } catch (e) {
          console.error(`Error in preview event listener for '${event}':`, e);
        }
      }
    }
  }

  public destroy(): void {
    this.isDestroyed = true;
    this.pause();
    this.unmount();
    if (this.proxyUnsubscribe) {
      this.proxyUnsubscribe();
      this.proxyUnsubscribe = null;
    }
    this.activeProxies.clear();
    this.proxyCoordinator = null;
    if (this.audioRuntime) {
      this.audioRuntime.destroy();
      this.audioRuntime = null;
    }
    this.listeners = {};
  }
}
