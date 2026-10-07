/**
 * compositor/master-compositor.ts — Engine-Neutral Master Compositor Architecture.
 * S28-R11: Central assembly and normalization orchestrator uniting multi-engine artifacts.
 * 
 * Pipeline:
 * Intermediate Artifacts (Canvas / Remotion / Stems)
 *   ↓
 * Master Compositor
 *   ↓
 * Output Normalization (Resolution, FPS, Codec, Audio Layout)
 *   ↓
 * Canonical Timeline & Scene Assembly (Duration & Transition Overlaps)
 *   ↓
 * Canonical Audio Normalization & Ducking (R07 Semantics)
 *   ↓
 * Final Multiplexed Video Artifact
 *   ↓
 * Canonical QC Gate Boundary
 */

import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFileSync } from "child_process";
import type { BlueprintV2, BlueprintScene } from "../contracts/blueprint";
import {
  type CompositorRequest,
  type CompositorResult,
  type CompositorMetrics,
  type CompositorInput,
  type OutputProfile,
  type NormalizedMediaInfo,
  MasterCompositorError,
  validateCompositorRequest,
  resolveProfileFromDocument,
} from "../contracts/compositor";
import { calculateCanonicalDuration, frameToSeconds } from "../contracts/timeline";
import { normalizeArtifactToSegment, findSystemFfmpeg } from "./output-normalizer";
import { extractAudioPlans, mixAndNormalizeAudio } from "./audio-normalizer";
import { assembleSceneSegments, type AssembledSceneSegment } from "./timeline-assembler";
import { probeMediaFile } from "./probe";

export interface MasterCompositorOptions {
  ffmpegPath?: string;
  ffprobePath?: string;
  defaultTempDir?: string;
  maxAvDriftMs?: number;
}

export class MasterCompositor {
  private readonly _ffmpegPath?: string;
  private readonly _ffprobePath?: string;
  private readonly _defaultTempDir?: string;
  private readonly _maxAvDriftMs: number;

  constructor(options?: MasterCompositorOptions) {
    this._ffmpegPath = options?.ffmpegPath;
    this._ffprobePath = options?.ffprobePath;
    this._defaultTempDir = options?.defaultTempDir;
    this._maxAvDriftMs = options?.maxAvDriftMs ?? 150;
  }

  /**
   * Main entrypoint for final video assembly and normalization.
   * Completely decoupled from concrete renderer internals.
   */
  async composite(request: CompositorRequest): Promise<CompositorResult> {
    const startTime = Date.now();
    let normTime = 0;
    let assemblyTime = 0;
    let audioTime = 0;
    let packagingTime = 0;

    // 1. Fail-closed request validation
    validateCompositorRequest(request);

    const doc = request.document;
    const profile = request.outputProfile;
    const signal = request.context?.signal;

    if (signal?.aborted) {
      throw new MasterCompositorError("CANCELLED", "Compositor execution cancelled prior to start");
    }

    // 2. Setup isolated working directory for intermediate normalized assets
    const baseTemp = request.context?.tempDir || this._defaultTempDir || os.tmpdir();
    const workDir = path.join(
      baseTemp,
      `compositor_${request.id}_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
    );
    fs.mkdirSync(workDir, { recursive: true });

    let finalOutputCreated = false;

    try {
      if (signal?.aborted) {
        throw new MasterCompositorError("CANCELLED", "Compositor execution cancelled");
      }

      // 3. Match inputs to canonical scenes fail-closed
      const scenes: BlueprintScene[] = doc.scenes ?? [];
      const assembledSegments: AssembledSceneSegment[] = [];

      const normStart = Date.now();

      for (let i = 0; i < scenes.length; i++) {
        if (signal?.aborted) {
          throw new MasterCompositorError("CANCELLED", "Compositor execution cancelled during normalization");
        }

        const scene = scenes[i];
        // Match input by canonicalSceneId, scope.id, or index
        const matchedInput =
          request.inputs.find((inp) => inp.canonicalSceneId === scene.scene_id) ||
          request.inputs.find((inp) => inp.artifact.scope.id === scene.scene_id) ||
          request.inputs[i];

        if (!matchedInput) {
          throw new MasterCompositorError(
            "MISSING_ARTIFACT",
            `No intermediate artifact provided for canonical scene '${scene.scene_id}' (index: ${i})`,
            { sceneId: scene.scene_id, sceneIndex: i }
          );
        }

        const artifact = matchedInput.artifact;
        const targetDurationFrames = matchedInput.targetDurationFrames ?? scene.durationFrames;
        const targetDurationSec = targetDurationFrames / profile.fps;

        const segmentPath = path.join(workDir, `norm_scene_${i}_${scene.scene_id}.mp4`);

        // Normalize visual artifact to target profile
        normalizeArtifactToSegment(artifact, profile, segmentPath, {
          signal,
          targetDurationSec,
          options: { ffmpegPath: this._ffmpegPath, ffprobePath: this._ffprobePath },
        });

        const transDurationFrames = scene.transition?.durationFrames ?? 0;
        const transDurationSec = transDurationFrames > 0 ? transDurationFrames / profile.fps : 0;

        assembledSegments.push({
          sceneId: scene.scene_id,
          segmentPath,
          durationSec: targetDurationSec,
          durationFrames: targetDurationFrames,
          transition:
            transDurationFrames > 0
              ? {
                  type: scene.transition?.type || "fade",
                  durationSec: transDurationSec,
                  durationFrames: transDurationFrames,
                }
              : undefined,
        });

        if (request.context?.onProgress) {
          request.context.onProgress((i + 1) / scenes.length * 0.4, `Normalized scene ${i + 1}/${scenes.length}`);
        }
      }

      normTime = Date.now() - normStart;

      if (signal?.aborted) {
        throw new MasterCompositorError("CANCELLED", "Compositor execution cancelled during scene assembly");
      }

      // 4. Canonical Timeline Assembly
      const assemblyStart = Date.now();
      const assembledVideoTrackPath = path.join(workDir, "assembled_visual_track.mp4");

      assembleSceneSegments({
        document: doc,
        segments: assembledSegments,
        profile,
        outputPath: assembledVideoTrackPath,
        signal,
        options: { ffmpegPath: this._ffmpegPath },
      });

      assemblyTime = Date.now() - assemblyStart;

      if (request.context?.onProgress) {
        request.context.onProgress(0.6, "Assembled video timeline");
      }

      if (signal?.aborted) {
        throw new MasterCompositorError("CANCELLED", "Compositor execution cancelled during audio processing");
      }

      // 5. Canonical Audio Normalization, Ducking & Mixing
      const audioStart = Date.now();
      const assembledAudioTrackPath = path.join(workDir, "assembled_audio_track.wav");

      const canonicalTotalFrames =
        (doc as any).totalDurationFrames ?? calculateCanonicalDuration(scenes);
      const canonicalDurationSec = canonicalTotalFrames / profile.fps;

      const audioPlans = extractAudioPlans(doc, request.audioStems);

      mixAndNormalizeAudio({
        plans: audioPlans,
        totalDurationSec: canonicalDurationSec,
        profile,
        outputPath: assembledAudioTrackPath,
        signal,
        options: { ffmpegPath: this._ffmpegPath },
      });

      audioTime = Date.now() - audioStart;

      if (request.context?.onProgress) {
        request.context.onProgress(0.8, "Mixed and normalized audio");
      }

      if (signal?.aborted) {
        throw new MasterCompositorError("CANCELLED", "Compositor execution cancelled during final packaging");
      }

      // 6. Multiplex Final Video + Audio into target outputPath
      const packagingStart = Date.now();
      fs.mkdirSync(path.dirname(request.outputPath), { recursive: true });

      const ffmpeg = this._ffmpegPath || findSystemFfmpeg();
      const muxArgs = [
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        assembledVideoTrackPath,
        "-i",
        assembledAudioTrackPath,
        "-c:v",
        "copy",
        "-c:a",
        profile.audioCodec,
        "-b:a",
        profile.audioBitrate,
        "-ar",
        String(profile.sampleRate),
        "-t",
        String(canonicalDurationSec),
        "-movflags",
        "+faststart",
        request.outputPath,
      ];

      execFileSync(ffmpeg, muxArgs, { stdio: "pipe" });
      finalOutputCreated = true;
      packagingTime = Date.now() - packagingStart;

      if (!fs.existsSync(request.outputPath)) {
        throw new MasterCompositorError(
          "COMPOSITION_FAILED",
          `Final packaged artifact not found at '${request.outputPath}'`,
          { outputPath: request.outputPath }
        );
      }

      // 7. Probe final output and verify against canonical authority
      const probed = probeMediaFile(request.outputPath, { ffprobePath: this._ffprobePath });
      const stat = fs.statSync(request.outputPath);

      const durationDriftMs = Math.abs(probed.durationSec - canonicalDurationSec) * 1000;
      if (durationDriftMs > this._maxAvDriftMs) {
        throw new MasterCompositorError(
          "AUDIO_SYNC_ERROR",
          `Final video duration (${probed.durationSec.toFixed(3)}s) drifted from canonical duration (${canonicalDurationSec.toFixed(3)}s) by ${durationDriftMs.toFixed(1)}ms (max allowed: ${this._maxAvDriftMs}ms)`,
          { probed, canonicalDurationSec, durationDriftMs }
        );
      }

      if (probed.width !== profile.width || probed.height !== profile.height) {
        throw new MasterCompositorError(
          "NORMALIZATION_FAILED",
          `Final video resolution (${probed.width}x${probed.height}) does not match target profile (${profile.width}x${profile.height})`,
          { probed, profile }
        );
      }

      const totalTimeMs = Date.now() - startTime;
      const metrics: CompositorMetrics = {
        totalDurationMs: totalTimeMs,
        normalizationTimeMs: normTime,
        assemblyTimeMs: assemblyTime,
        audioProcessingTimeMs: audioTime,
        finalPackagingTimeMs: packagingTime,
        inputCount: request.inputs.length,
        temporaryDiskBytes: stat.size,
        peakMemoryBytes: process.memoryUsage().heapUsed,
      };

      const mediaInfo: NormalizedMediaInfo = {
        width: probed.width,
        height: probed.height,
        fps: probed.fps,
        durationSec: probed.durationSec,
        durationFrames: probed.durationFrames || Math.round(probed.durationSec * profile.fps),
        videoCodec: probed.videoCodec || profile.videoCodec,
        pixelFormat: probed.pixelFormat,
        audioCodec: probed.audioCodec,
        sampleRate: probed.audioSampleRate,
        channels: probed.audioChannels,
        fileSizeBytes: stat.size,
      };

      if (request.context?.onProgress) {
        request.context.onProgress(1.0, "Composition complete");
      }

      return {
        ok: true,
        requestId: request.id,
        outputPath: request.outputPath,
        outputProfile: profile,
        mediaInfo,
        metrics,
      };
    } catch (err: any) {
      // If error or cancelled and partial output exists, clean it up
      if (!finalOutputCreated && fs.existsSync(request.outputPath)) {
        try {
          fs.unlinkSync(request.outputPath);
        } catch {
          // ignore
        }
      }

      if (err instanceof MasterCompositorError) {
        throw err;
      }

      throw new MasterCompositorError(
        "COMPOSITION_FAILED",
        `MasterCompositor failed: ${err?.message || String(err)}`,
        { error: String(err) }
      );
    } finally {
      // Clean up isolated temporary working directory completely
      if (fs.existsSync(workDir)) {
        try {
          fs.rmSync(workDir, { recursive: true, force: true });
        } catch {
          // ignore
        }
      }
    }
  }
}
