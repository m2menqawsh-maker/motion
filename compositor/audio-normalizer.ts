/**
 * compositor/audio-normalizer.ts — Canonical Audio Subsystem Normalizer & Ducking Mixer.
 * S28-R11: Preserves R07 audio timing, multi-track mixing, and dynamic ducking semantics.
 */

import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";
import type { BlueprintV2 } from "../contracts/blueprint";
import {
  type AudioStemInput,
  type OutputProfile,
  MasterCompositorError,
} from "../contracts/compositor";
import { findSystemFfmpeg } from "./output-normalizer";

export interface AudioNormalizerOptions {
  ffmpegPath?: string;
  assetResolver?: (assetRef: string) => string | undefined;
}

export interface AudioTrackPlan {
  role: "voiceover" | "music" | "sfx" | "stem";
  filePath: string;
  startSec: number;
  durationSec: number;
  volume: number;
  mute: boolean;
  loop?: boolean;
  ducking?: {
    enabled: boolean;
    duckingVolume: number;
    duckUnderRoles: string[];
  };
}

/**
 * Extracts normalized audio track plans from a Canonical VideoDocument and explicit AudioStems.
 */
export function extractAudioPlans(
  doc: BlueprintV2,
  explicitStems?: AudioStemInput[],
  resolver?: (ref: string) => string | undefined
): AudioTrackPlan[] {
  const fps = doc.fps || 30;
  const plans: AudioTrackPlan[] = [];

  const resolvePath = (ref: string): string => {
    if (fs.existsSync(ref)) return ref;
    if (resolver) {
      const resolved = resolver(ref);
      if (resolved && fs.existsSync(resolved)) return resolved;
    }
    const mediaMap = (doc as any).media_map || (doc as any).mediaMap;
    if (mediaMap && mediaMap[ref]) {
      const mapped = mediaMap[ref];
      if (fs.existsSync(mapped)) return mapped;
      const mappedResolved = path.resolve(process.cwd(), mapped);
      if (fs.existsSync(mappedResolved)) return mappedResolved;
      const mappedPub = path.resolve(process.cwd(), "remotion-app/public", mapped);
      if (fs.existsSync(mappedPub)) return mappedPub;
    }
    // Check known test asset directories
    const testCandidates = [
      path.resolve(process.cwd(), ref),
      path.resolve(process.cwd(), "assets/incoming/tests", ref),
      path.resolve(process.cwd(), "assets/ready/audio", ref),
      path.resolve(process.cwd(), "public", ref),
      path.resolve(process.cwd(), "remotion-app/public", ref),
    ];
    for (const c of testCandidates) {
      if (fs.existsSync(c)) return c;
      if (fs.existsSync(`${c}.wav`)) return `${c}.wav`;
      if (fs.existsSync(`${c}.mp3`)) return `${c}.mp3`;
    }
    return ref;
  };

  // 1. Process explicit AudioStem inputs if provided
  if (explicitStems && explicitStems.length > 0) {
    for (const stem of explicitStems) {
      const resolved = resolvePath(stem.filePath);
      const startSec = stem.startFrame / fps;
      const durationSec = stem.durationFrames ? stem.durationFrames / fps : 0;
      plans.push({
        role: stem.role === "voiceover" ? "voiceover" : stem.role === "music" ? "music" : "sfx",
        filePath: resolved,
        startSec,
        durationSec,
        volume: stem.volume,
        mute: stem.mute ?? false,
        loop: stem.loop ?? false,
        ducking: stem.ducking
          ? {
              enabled: stem.ducking.enabled,
              duckingVolume: stem.ducking.duckingVolume,
              duckUnderRoles: stem.ducking.duckUnderRoles ?? ["voiceover"],
            }
          : undefined,
      });
    }
    return plans;
  }

  // 2. Process canonical AudioPlan from doc.audio
  const audio = doc.audio;
  if (!audio) return plans;

  // Voiceover
  if (audio.voiceover) {
    const vo = audio.voiceover;
    const ref = typeof vo.asset_ref === "string" ? vo.asset_ref : (vo.asset_ref as any)?.asset_id || (vo as any).file;
    if (ref) {
      const startSec = (vo.startFrame ?? 0) / fps;
      const durationSec = vo.durationFrames ? vo.durationFrames / fps : 0;
      plans.push({
        role: "voiceover",
        filePath: resolvePath(ref),
        startSec,
        durationSec,
        volume: vo.volume ?? 1.0,
        mute: vo.mute ?? false,
      });
    }
  }

  // Music
  if (audio.music) {
    const bgm = audio.music;
    const ref = typeof bgm.asset_ref === "string" ? bgm.asset_ref : (bgm.asset_ref as any)?.asset_id || (bgm as any).file;
    if (ref) {
      const startSec = (bgm.startFrame ?? 0) / fps;
      const durationSec = bgm.durationFrames ? bgm.durationFrames / fps : 0;
      plans.push({
        role: "music",
        filePath: resolvePath(ref),
        startSec,
        durationSec,
        volume: bgm.volume ?? 0.15,
        mute: bgm.mute ?? false,
        loop: bgm.loop ?? true,
        ducking: bgm.ducking
          ? {
              enabled: bgm.ducking.enabled !== false,
              duckingVolume: bgm.ducking.ducking_volume ?? 0.05,
              duckUnderRoles: bgm.ducking.duck_under ?? ["voiceover"],
            }
          : undefined,
      });
    }
  }

  // SFX
  if (audio.global_sfx && Array.isArray(audio.global_sfx)) {
    for (const sfx of audio.global_sfx) {
      const ref = typeof sfx.asset_ref === "string" ? sfx.asset_ref : (sfx.asset_ref as any)?.asset_id || (sfx as any).file;
      if (ref) {
        const startSec = (sfx.startFrame ?? 0) / fps;
        const durationSec = sfx.durationFrames ? sfx.durationFrames / fps : 0;
        plans.push({
          role: "sfx",
          filePath: resolvePath(ref),
          startSec,
          durationSec,
          volume: sfx.volume ?? 1.0,
          mute: sfx.mute ?? false,
        });
      }
    }
  }

  return plans;
}

/**
 * Mixes and normalizes all canonical audio streams into a single synchronized audio track.
 */
export function mixAndNormalizeAudio(params: {
  plans: AudioTrackPlan[];
  totalDurationSec: number;
  profile: OutputProfile;
  outputPath: string;
  signal?: AbortSignal;
  options?: AudioNormalizerOptions;
}): void {
  if (params.signal?.aborted) {
    throw new MasterCompositorError("CANCELLED", "Audio mixing aborted via signal");
  }

  const ffmpeg = params.options?.ffmpegPath || findSystemFfmpeg();
  const activePlans = params.plans.filter((p) => !p.mute);

  fs.mkdirSync(path.dirname(params.outputPath), { recursive: true });

  const isWav = params.outputPath.endsWith(".wav");
  const codec = isWav ? "pcm_s16le" : params.profile.audioCodec;

  // If no audio plans exist, synthesize exact-duration silence
  if (activePlans.length === 0) {
    const ffmpegArgs = [
      "-y",
      "-hide_banner",
      "-loglevel",
      "error",
      "-f",
      "lavfi",
      "-t",
      String(params.totalDurationSec),
      "-i",
      `anullsrc=r=${params.profile.sampleRate}:cl=${params.profile.channelLayout}`,
      "-c:a",
      codec,
      "-ar",
      String(params.profile.sampleRate),
    ];
    if (!isWav) {
      ffmpegArgs.push("-b:a", params.profile.audioBitrate);
    }
    ffmpegArgs.push(params.outputPath);
    execFileSync(ffmpeg, ffmpegArgs, { stdio: "pipe" });
    return;
  }

  // Verify all audio files exist
  for (const p of activePlans) {
    if (!fs.existsSync(p.filePath)) {
      throw new MasterCompositorError(
        "MISSING_ARTIFACT",
        `Canonical audio file not found on disk: '${p.filePath}' (role: ${p.role})`,
        { plan: p }
      );
    }
  }

  // Voiceover time range for dynamic ducking
  const voPlan = activePlans.find((p) => p.role === "voiceover");
  const voStart = voPlan ? voPlan.startSec : 0;
  const voEnd = voPlan && voPlan.durationSec > 0 ? voPlan.startSec + voPlan.durationSec : voStart;

  // Build FFmpeg complex filter
  const ffmpegArgs: string[] = ["-y", "-hide_banner", "-loglevel", "error"];
  const filterNodes: string[] = [];
  const mixedLabels: string[] = [];

  activePlans.forEach((plan, idx) => {
    // Add input
    if (plan.loop && plan.role === "music") {
      ffmpegArgs.push("-stream_loop", "-1", "-i", plan.filePath);
    } else {
      ffmpegArgs.push("-i", plan.filePath);
    }

    const inputLabel = `[${idx}:a]`;
    const resampledLabel = `[resampled_${idx}]`;
    const delayedLabel = `[delayed_${idx}]`;
    const outLabel = `[proc_${idx}]`;

    // 1. Resample and channel match
    filterNodes.push(
      `${inputLabel}aresample=${params.profile.sampleRate}:async=1,pan=${params.profile.channelLayout}|c0=c0|c1=c1${resampledLabel}`
    );

    // 2. Start delay & trim
    const delayMs = Math.max(0, Math.round(plan.startSec * 1000));
    let timeChain = resampledLabel;

    if (delayMs > 0) {
      filterNodes.push(`${timeChain}adelay=${delayMs}|${delayMs}${delayedLabel}`);
      timeChain = delayedLabel;
    }

    if (plan.durationSec > 0 && plan.role !== "music") {
      const trimmedLabel = `[trimmed_${idx}]`;
      const endSec = plan.startSec + plan.durationSec;
      filterNodes.push(`${timeChain}atrim=0:${endSec},asetpts=PTS-STARTPTS${trimmedLabel}`);
      timeChain = trimmedLabel;
    }

    // 3. Volume & Ducking
    if (plan.role === "music" && plan.ducking?.enabled && voPlan && voEnd > voStart) {
      // Dynamic Ducking: Lower volume during voiceover active window
      const baseVol = plan.volume;
      const duckVol = plan.ducking.duckingVolume;
      filterNodes.push(
        `${timeChain}volume=eval=frame:volume='if(between(t,${voStart.toFixed(3)},${voEnd.toFixed(3)}),${duckVol.toFixed(3)},${baseVol.toFixed(3)})'${outLabel}`
      );
    } else {
      // Fixed volume
      filterNodes.push(`${timeChain}volume=${plan.volume.toFixed(3)}${outLabel}`);
    }

    mixedLabels.push(outLabel);
  });

  // 4. Mix all processed tracks
  if (mixedLabels.length === 1) {
    filterNodes.push(
      `${mixedLabels[0]}atrim=0:${params.totalDurationSec.toFixed(3)},asetpts=PTS-STARTPTS[final_a]`
    );
  } else {
    filterNodes.push(
      `${mixedLabels.join("")}amix=inputs=${mixedLabels.length}:duration=longest:dropout_transition=0,atrim=0:${params.totalDurationSec.toFixed(3)},asetpts=PTS-STARTPTS[final_a]`
    );
  }

  ffmpegArgs.push("-filter_complex", filterNodes.join(";"));
  ffmpegArgs.push(
    "-map",
    "[final_a]",
    "-c:a",
    codec,
    "-ar",
    String(params.profile.sampleRate),
    "-t",
    String(params.totalDurationSec)
  );
  if (!isWav) {
    ffmpegArgs.push("-b:a", params.profile.audioBitrate);
  }
  ffmpegArgs.push(params.outputPath);


  try {
    execFileSync(ffmpeg, ffmpegArgs, { stdio: "pipe" });
  } catch (err: any) {
    if (params.signal?.aborted) {
      throw new MasterCompositorError("CANCELLED", "Audio mixing aborted via signal");
    }
    throw new MasterCompositorError(
      "NORMALIZATION_FAILED",
      `Failed to mix and normalize audio: ${err?.message || String(err)}`,
      { args: ffmpegArgs, error: String(err) }
    );
  }

  if (!fs.existsSync(params.outputPath)) {
    throw new MasterCompositorError(
      "NORMALIZATION_FAILED",
      `Normalized audio was not produced at '${params.outputPath}'`,
      { outputPath: params.outputPath }
    );
  }
}
