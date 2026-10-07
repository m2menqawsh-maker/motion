/**
 * tests/remotion/s28_r07_critical_integration.test.ts
 * Critical Integration Gate Test for S28-R07:
 * TemplateSpec -> instantiate canonical project -> add/use audio track
 *   -> BrowserPreviewRuntime -> play -> audio + visual sync -> seek
 *   -> audio remains aligned -> audio mutation -> ChangeSet
 *   -> preview updates -> undo -> redo.
 */
import { describe, it, expect } from "vitest";
import { instantiateTemplate } from "../../contracts/template-instantiator";
import { EditorSession } from "../../contracts/editor-session";
import { BrowserPreviewRuntime } from "../../preview/preview-runtime";
import { AudioPreviewRuntime } from "../../preview/audio/audio-preview-runtime";
import {
  MockWebAudioContext,
  createSyntheticAudioBuffer,
} from "../../preview/audio/web-audio-adapter";
import type { BlueprintV2 } from "../../contracts/blueprint";

describe("S28-R07 Critical Integration Pipeline Test", () => {
  it("CRIT-01: Full Lifecycle — TemplateSpec -> Instantiate -> Audio Track -> Preview -> Play -> Sync -> Seek -> Mutation -> ChangeSet -> Undo -> Redo", () => {
    // 1. TemplateSpec -> instantiate canonical scene
    const inst = instantiateTemplate(
      "rui-title-card",
      {
        title: "منظومة الصوت الموحدة",
        subtitle: "S28-R07 Audio Preview & Sync",
        backgroundColor: "#0f172a",
        accentColor: "#38bdf8",
      },
      { scene_id: "scene_crit_01", startFrame: 0, durationFrames: 90 }
    );

    // 2. Canonical project with audio track definitions
    const canonicalProject: BlueprintV2 = {
      blueprint_version: "2.0.0",
      project_id: "crit_audio_project",
      fps: 30,
      aspect_ratio: "16:9",
      scenes: [inst.scene],
      audio: {
        voiceover: {
          asset_ref: "vo_narrator_master",
          startFrame: 0,
          durationFrames: 60, // 0 to 60 (2.0s)
          volume: 1.0,
          mute: false,
        },
        music: {
          asset_ref: "bgm_acoustic_master",
          startFrame: 0,
          durationFrames: 90, // whole duration (3.0s)
          volume: 0.3,
          loop: true,
          mute: false,
          ducking: {
            enabled: true,
            ducking_volume: 0.05,
            duck_under: ["voiceover"],
          },
        },
      },
    };

    // 3. Initialize EditorSession
    const session = new EditorSession(canonicalProject);
    expect(session.getRevision()).toBe(0);

    // 4. Set up BrowserPreviewRuntime with AudioPreviewRuntime
    const mockCtx = new MockWebAudioContext();
    const audioRuntime = new AudioPreviewRuntime({
      audioContext: mockCtx,
    });

    const voBuffer = createSyntheticAudioBuffer(mockCtx, { durationSec: 3.0, frequency: 350 });
    const musicBuffer = createSyntheticAudioBuffer(mockCtx, { durationSec: 10.0, frequency: 180 });
    audioRuntime.registerAudioBuffer("vo_narrator_master", voBuffer);
    audioRuntime.registerAudioBuffer("bgm_acoustic_master", musicBuffer);

    const previewRuntime = new BrowserPreviewRuntime(session.getPreviewBlueprint(), {
      audioRuntime,
      clockMode: "manual",
    });

    // 5. Play -> Audio + Visual Synchronized
    previewRuntime.play();
    expect(previewRuntime.getState()).toBe("playing");
    expect(audioRuntime.getState()).toBe("playing");

    const visualFrame0 = previewRuntime.getCurrentVisualFrame()!;
    expect(visualFrame0.activeScenes).toContain("scene_crit_01");
    expect(visualFrame0.nodes.some((n) => n.text === "منظومة الصوت الموحدة")).toBe(true);

    const voTrack = audioRuntime.getTrack("audio_voiceover")!;
    const musicTrack = audioRuntime.getTrack("audio_music")!;
    expect(voTrack.isPlaying).toBe(true);
    expect(musicTrack.isPlaying).toBe(true);
    expect(voTrack.sourceNode.startOffset).toBeCloseTo(0.0, 3);
    expect(musicTrack.sourceNode.startOffset).toBeCloseTo(0.0, 3);

    // 6. Seek -> Audio remains aligned
    previewRuntime.seek(30); // 1.0 second into video
    expect(previewRuntime.getCurrentFrame()).toBe(30);

    const visualFrame30 = previewRuntime.getCurrentVisualFrame()!;
    expect(visualFrame30.frame).toBe(30);

    // Both audio sources restarted at 1.0s offset
    expect(voTrack.isPlaying).toBe(true);
    expect(musicTrack.isPlaying).toBe(true);
    expect(voTrack.sourceNode.startOffset).toBeCloseTo(1.0, 3);
    expect(musicTrack.sourceNode.startOffset).toBeCloseTo(1.0, 3);

    // 7. Audio Mutation -> ChangeSet -> Preview Updates
    const originalMusicSource = musicTrack.sourceNode;
    const mutResult = session.applyMutation({
      mutation_id: "mut_level_change_01",
      type: "SET_AUDIO_LEVEL",
      author: "user",
      payload: {
        track: "music",
        volume: 0.85,
      },
    });

    expect(mutResult.success).toBe(true);
    expect(mutResult.changeset.invalidation.requires_audio_remix).toBe(true);
    expect(mutResult.changeset.invalidation.requires_timeline_rebuild).toBe(false);

    // Preview updates from session draft
    previewRuntime.updateDocument(session.getPreviewBlueprint(), mutResult.changeset);

    // Music track descriptor updated
    expect(musicTrack.descriptor.volume).toBe(0.85);
    // Crucial: source node was NOT interrupted or recreated during partial level change
    expect(musicTrack.sourceNode).toBe(originalMusicSource);

    // 8. Undo -> Restore volume to 0.3
    const undoResult = session.undo();
    expect(undoResult.success).toBe(true);
    expect(undoResult.changeset).toBeDefined();

    previewRuntime.updateDocument(session.getPreviewBlueprint(), undoResult.changeset);
    expect(musicTrack.descriptor.volume).toBe(0.3);

    // 9. Redo -> Re-apply volume to 0.85
    const redoResult = session.redo();
    expect(redoResult.success).toBe(true);
    expect(redoResult.changeset).toBeDefined();

    previewRuntime.updateDocument(session.getPreviewBlueprint(), redoResult.changeset);
    expect(musicTrack.descriptor.volume).toBe(0.85);

    // 10. Clean up
    previewRuntime.destroy();
    expect(previewRuntime.getAudioRuntime()).toBeNull();
  });
});
