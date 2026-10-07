/**
 * tests/remotion/s28_r07_audio_core.test.ts
 * Core Verification Suite for S28-R07: Audio Preview, Synchronization & Mixing.
 * Enforces:
 *   - Play / Pause / Seek / Step synchronization with BrowserPreviewRuntime
 *   - Zero independent timeline clock (preview playhead remains single authority)
 *   - Multi-track mixing (voiceover, music, global_sfx, layer audio)
 *   - Dynamic voiceover ducking
 *   - Volume / mute mutations update audio graph without full teardown
 *   - Playback rate synchronization
 *   - Drift detection & correction policy
 *   - Explicit fail-closed structured diagnostics for missing/invalid assets
 */
import { describe, it, expect } from "vitest";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import { AudioPreviewRuntime } from "../../preview/audio/audio-preview-runtime";
import {
  MockWebAudioContext,
  createSyntheticAudioBuffer,
} from "../../preview/audio/web-audio-adapter";
import { AudioDiagnosticError } from "../../preview/audio/audio-types";
import { applyMutation, type BlueprintV2, type CanonicalMutation } from "../../contracts";

describe("S28-R07 Audio Preview Core, Synchronization & Mixing", () => {
  function createTestAudioBlueprint(): BlueprintV2 {
    return {
      blueprint_version: "2.0.0",
      project_id: "audio_sync_project",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [
        {
          scene_id: "scene_01",
          template: "rui-title-card",
          startFrame: 0,
          durationFrames: 60, // 2.0s
          surface: { text: "Scene One" },
        },
        {
          scene_id: "scene_02",
          template: "rui-title-card",
          startFrame: 60,
          durationFrames: 60, // 2.0s
          surface: { text: "Scene Two" },
        },
      ],
      audio: {
        voiceover: {
          asset_ref: "vo_narrator_01",
          startFrame: 15,
          durationFrames: 45, // frames 15 to 60
          volume: 0.9,
          mute: false,
        },
        music: {
          asset_ref: "bgm_upbeat_01",
          startFrame: 0,
          durationFrames: 120, // whole video
          volume: 0.4,
          loop: true,
          mute: false,
          ducking: {
            enabled: true,
            ducking_volume: 0.1,
            duck_under: ["voiceover"],
          },
        },
        global_sfx: [
          {
            asset_ref: "sfx_whoosh_01",
            startFrame: 30,
            durationFrames: 15, // frames 30 to 45
            volume: 0.8,
          },
        ],
      },
    };
  }

  function setupRuntimeWithAudio(blueprint: BlueprintV2) {
    const mockCtx = new MockWebAudioContext();
    const audioRuntime = new AudioPreviewRuntime({
      audioContext: mockCtx,
      syncPolicy: { maxDriftToleranceMs: 40, hardResyncThresholdMs: 100 },
    });

    // Pre-populate buffers for tests
    const voBuf = createSyntheticAudioBuffer(mockCtx, { durationSec: 5.0, frequency: 300 });
    const musicBuf = createSyntheticAudioBuffer(mockCtx, { durationSec: 10.0, frequency: 150 });
    const sfxBuf = createSyntheticAudioBuffer(mockCtx, { durationSec: 1.0, frequency: 600 });

    audioRuntime.registerAudioBuffer("vo_narrator_01", voBuf);
    audioRuntime.registerAudioBuffer("bgm_upbeat_01", musicBuf);
    audioRuntime.registerAudioBuffer("sfx_whoosh_01", sfxBuf);

    const previewRuntime = new BrowserPreviewRuntime(blueprint, {
      audioRuntime,
      clockMode: "manual",
    });

    return { previewRuntime, audioRuntime, mockCtx, voBuf, musicBuf, sfxBuf };
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 1. Play / Pause / Seek Synchronization
  // ──────────────────────────────────────────────────────────────────────────

  it("AUD-01: Play starts video and audio synchronized at canonical playhead frame", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime, mockCtx } = setupRuntimeWithAudio(bp);

    // Initial state: frame 0, paused
    expect(previewRuntime.getCurrentFrame()).toBe(0);
    expect(audioRuntime.getState()).toBe("idle");

    previewRuntime.play();

    expect(previewRuntime.getState()).toBe("playing");
    expect(audioRuntime.getState()).toBe("playing");

    // At frame 0: music is within [0..120], voiceover is [15..60] (not yet), sfx is [30..45] (not yet)
    const musicTrack = audioRuntime.getTrack("audio_music");
    const voTrack = audioRuntime.getTrack("audio_voiceover");

    expect(musicTrack?.isPlaying).toBe(true);
    expect(musicTrack?.sourceNode?.startOffset).toBe(0); // Offset 0 sec
    expect(voTrack?.isPlaying).toBe(false); // Should not start yet

    previewRuntime.destroy();
  });

  it("AUD-02: Pause stops audio at the exact discrete logical frame", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime } = setupRuntimeWithAudio(bp);

    previewRuntime.play();
    previewRuntime.pause();

    expect(previewRuntime.getState()).toBe("paused");
    expect(audioRuntime.getState()).toBe("paused");

    const musicTrack = audioRuntime.getTrack("audio_music");
    expect(musicTrack?.isPlaying).toBe(false);

    previewRuntime.destroy();
  });

  it("AUD-03: Seek calculates exact buffer offset based on canonical frame and restarts active tracks", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime } = setupRuntimeWithAudio(bp);

    previewRuntime.play();

    // Seek to frame 30 (1.0 second into the 30fps video)
    // At frame 30:
    // - music started at frame 0 -> offset is 30/30 = 1.0 second
    // - voiceover started at frame 15 -> offset is (30 - 15)/30 = 0.5 second
    // - sfx started at frame 30 -> offset is (30 - 30)/30 = 0.0 second
    previewRuntime.seek(30);

    expect(previewRuntime.getCurrentFrame()).toBe(30);

    const musicTrack = audioRuntime.getTrack("audio_music");
    const voTrack = audioRuntime.getTrack("audio_voiceover");
    const sfxTrack = audioRuntime.getTrack("audio_sfx_0");

    expect(musicTrack?.isPlaying).toBe(true);
    expect(musicTrack?.sourceNode?.startOffset).toBeCloseTo(1.0, 3);

    expect(voTrack?.isPlaying).toBe(true);
    expect(voTrack?.sourceNode?.startOffset).toBeCloseTo(0.5, 3);

    expect(sfxTrack?.isPlaying).toBe(true);
    expect(sfxTrack?.sourceNode?.startOffset).toBeCloseTo(0.0, 3);

    previewRuntime.destroy();
  });

  it("AUD-04: Step forward and step backward preserve audio alignment without timeline drift", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime } = setupRuntimeWithAudio(bp);

    previewRuntime.play();
    previewRuntime.seek(15);

    const voTrack = audioRuntime.getTrack("audio_voiceover");
    expect(voTrack?.isPlaying).toBe(true);
    expect(voTrack?.sourceNode?.startOffset).toBeCloseTo(0.0, 3);

    // Step forward 15 frames -> frame 30
    previewRuntime.stepForward(15);
    expect(previewRuntime.getCurrentFrame()).toBe(30);
    expect(voTrack?.sourceNode?.startOffset).toBeCloseTo(0.5, 3);

    // Step backward 10 frames -> frame 20
    previewRuntime.stepBackward(10);
    expect(previewRuntime.getCurrentFrame()).toBe(20);
    expect(voTrack?.sourceNode?.startOffset).toBeCloseTo(5 / 30, 3);

    previewRuntime.destroy();
  });

  it("AUD-05: PlaybackRate updates active audio buffer sources synchronously", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime } = setupRuntimeWithAudio(bp);

    previewRuntime.play();
    const musicTrack = audioRuntime.getTrack("audio_music");
    expect(musicTrack?.sourceNode?.playbackRate.value).toBe(1.0);

    previewRuntime.setPlaybackRate(1.5);
    expect(previewRuntime.getPlaybackRate()).toBe(1.5);
    expect(musicTrack?.sourceNode?.playbackRate.value).toBe(1.5);

    previewRuntime.destroy();
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Multi-Track Mixing & Dynamic Ducking
  // ──────────────────────────────────────────────────────────────────────────

  it("AUD-06: Multi-track mixing — voiceover, music and sfx tracks mix into master gain", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime } = setupRuntimeWithAudio(bp);

    expect(audioRuntime.getTrackCount()).toBe(3); // voiceover, music, sfx_0

    previewRuntime.seek(35); // all 3 active
    previewRuntime.play();

    const musicTrack = audioRuntime.getTrack("audio_music");
    const voTrack = audioRuntime.getTrack("audio_voiceover");
    const sfxTrack = audioRuntime.getTrack("audio_sfx_0");

    expect(musicTrack?.isPlaying).toBe(true);
    expect(voTrack?.isPlaying).toBe(true);
    expect(sfxTrack?.isPlaying).toBe(true);

    previewRuntime.destroy();
  });

  it("AUD-07: Dynamic voiceover ducking — music ducks when voiceover is active", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime } = setupRuntimeWithAudio(bp);

    // Frame 5: voiceover not active (starts at frame 15)
    // Music volume should be full (0.4)
    previewRuntime.seek(5);
    previewRuntime.play();
    const musicTrack = audioRuntime.getTrack("audio_music");
    expect(musicTrack?.gainNode.gain.value).toBe(0.4);

    // Frame 20: voiceover active (15..60)
    // Music volume should duck to 0.1
    previewRuntime.seek(20);
    expect(musicTrack?.gainNode.gain.value).toBe(0.1);

    // Frame 70: voiceover ended (60+)
    // Music volume should recover to 0.4
    previewRuntime.seek(70);
    expect(musicTrack?.gainNode.gain.value).toBe(0.4);

    previewRuntime.destroy();
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Mutation Integration (ChangeSet & Invalidation)
  // ──────────────────────────────────────────────────────────────────────────

  it("AUD-08: SET_AUDIO_LEVEL mutation updates volume/mute immediately without rebuilding sources", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime } = setupRuntimeWithAudio(bp);

    previewRuntime.seek(5);
    previewRuntime.play();

    const musicTrack = audioRuntime.getTrack("audio_music");
    const originalSource = musicTrack?.sourceNode;
    expect(musicTrack?.gainNode.gain.value).toBe(0.4);

    // Apply SET_AUDIO_LEVEL mutation
    const mutation: CanonicalMutation = {
      mutation_id: "mut_audio_vol_01",
      type: "SET_AUDIO_LEVEL",
      author: "user",
      payload: {
        track: "music",
        volume: 0.8,
      },
    };

    const res = applyMutation(bp, mutation);
    expect(res.success).toBe(true);
    expect(res.changeset.invalidation.requires_timeline_rebuild).toBe(false);
    expect(res.changeset.invalidation.requires_audio_remix).toBe(true);

    // Push mutation to runtime
    previewRuntime.updateDocument(res.blueprint, res.changeset);

    // Gain node updated to 0.8
    expect(musicTrack?.gainNode.gain.value).toBe(0.8);
    // Crucial: source node was NOT recreated or interrupted!
    expect(musicTrack?.sourceNode).toBe(originalSource);

    previewRuntime.destroy();
  });

  it("AUD-09: Audio track timing mutation triggers safe rescheduling of audio sources", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime } = setupRuntimeWithAudio(bp);

    previewRuntime.seek(10);
    previewRuntime.play();

    const voTrack = audioRuntime.getTrack("audio_voiceover");
    // Initially starts at frame 15, so at frame 10 it is not playing
    expect(voTrack?.isPlaying).toBe(false);

    // Shift voiceover startFrame from 15 to 5
    const mutation: CanonicalMutation = {
      mutation_id: "mut_audio_shift_01",
      type: "UPDATE_AUDIO",
      author: "user",
      payload: {
        voiceover: {
          startFrame: 5,
        },
      },
    };

    const res = applyMutation(bp, mutation);
    expect(res.success).toBe(true);
    expect(res.changeset.invalidation.requires_timeline_rebuild).toBe(true);

    previewRuntime.updateDocument(res.blueprint, res.changeset);

    // Now at frame 10, voiceover (5..50) IS active!
    expect(voTrack?.isPlaying).toBe(true);
    expect(voTrack?.sourceNode?.startOffset).toBeCloseTo((10 - 5) / 30, 3);

    previewRuntime.destroy();
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 4. Drift Policy & Error Handling
  // ──────────────────────────────────────────────────────────────────────────

  it("AUD-10: Small drift detection policy detects drift and emits driftCorrected event", () => {
    const bp = createTestAudioBlueprint();
    const { previewRuntime, audioRuntime, mockCtx } = setupRuntimeWithAudio(bp);

    previewRuntime.play();
    let driftReported = false;

    audioRuntime.on("driftCorrected", (driftMs) => {
      driftReported = true;
      expect(driftMs).toBeGreaterThan(40);
    });

    // Artificially advance mock context clock by 250ms ahead of preview ticks
    mockCtx.advanceTime(0.25);
    audioRuntime.syncFrame(previewRuntime.getCurrentFrame());

    expect(driftReported).toBe(true);

    previewRuntime.destroy();
  });

  it("AUD-11: Missing asset with failClosedOnMissingAsset throws structured AudioDiagnosticError", () => {
    const mockCtx = new MockWebAudioContext();
    const audioRuntime = new AudioPreviewRuntime({
      audioContext: mockCtx,
      failClosedOnMissingAsset: true,
    });

    const bp = createTestAudioBlueprint();
    // Do NOT register buffers
    expect(() => {
      audioRuntime.syncDocument(bp);
      audioRuntime.syncPlay(0);
    }).toThrow(AudioDiagnosticError);

    const diagnostics = audioRuntime.getDiagnostics();
    expect(diagnostics.length).toBeGreaterThan(0);
    expect(diagnostics[0].code).toBe("MISSING_ASSET");
  });

  it("AUD-12: Corrupted audio stream triggers explicit DECODE_FAILURE diagnostic", async () => {
    const mockCtx = new MockWebAudioContext();
    const audioRuntime = new AudioPreviewRuntime({
      audioContext: mockCtx,
    });

    // Buffer with corruption header [0xde, 0xad]
    const corruptBuffer = new Uint8Array([0xde, 0xad, 0xbe, 0xef]).buffer;

    await expect(
      audioRuntime.loadAudioFromBuffer("corrupt_asset", corruptBuffer)
    ).rejects.toThrowError(AudioDiagnosticError);

    const diag = audioRuntime.getDiagnostics().find((d) => d.code === "DECODE_FAILURE");
    expect(diag).toBeDefined();
  });
});
