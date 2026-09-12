import { buildVideo } from '../../remotion-app/src/engine/orchestration/BuildEngine';
import { VideoSpec } from '../../remotion-app/src/engine/orchestration/types';

function runTests() {
  console.log('--- STARTING ORCHESTRATION TESTS ---\n');
  let passed = 0;
  let total = 0;

  function assertBuild(name: string, spec: VideoSpec, expectedBlocked: boolean, expectedErrorStage?: string) {
    total++;
    console.log(`Test: ${name}`);
    const result = buildVideo(spec, { dryRun: true });
    
    if (expectedBlocked) {
      if (!result.success) {
        if (expectedErrorStage) {
          const hasStage = result.errors.some(e => e.stage === expectedErrorStage);
          if (hasStage) {
            console.log('✅ PASS (Blocked correctly with expected stage)\n');
            passed++;
          } else {
            console.log(`❌ FAIL (Blocked but wrong stage. Expected: ${expectedErrorStage})\n`, result.errors);
          }
        } else {
          console.log('✅ PASS (Blocked correctly)\n');
          passed++;
        }
      } else {
        console.log('❌ FAIL (Expected blocked, but succeeded)\n');
      }
    } else {
      if (result.success) {
        console.log('✅ PASS (Succeeded correctly)\n');
        passed++;
      } else {
        console.log('❌ FAIL (Expected success, but blocked)\n', result.errors);
      }
    }
  }

  // Test A - Valid Build
  assertBuild('Test A - Valid Build', {
    id: 'test-a',
    width: 1920,
    height: 1080,
    fps: 30,
    durationInFrames: 60,
    scenes: [
      {
        id: 'scene-1',
        templateId: 'scenes/ChaosDesktop',
        durationInFrames: 60,
        startFrame: 0
      }
    ]
  }, false);

  // Test B - Invalid Props (Missing Required)
  assertBuild('Test B - Invalid Props (Missing Required)', {
    id: 'test-b',
    width: 1920,
    height: 1080,
    fps: 30,
    durationInFrames: 60,
    scenes: [
      {
        id: 'scene-1',
        templateId: 'camera/AutoZoom',
        props: {},
        durationInFrames: 60,
        startFrame: 0
      }
    ]
  }, true, 'PROPS_GATE');

  // Test C - Missing Template
  assertBuild('Test C - Missing Template', {
    id: 'test-c',
    width: 1920,
    height: 1080,
    fps: 30,
    durationInFrames: 60,
    scenes: [
      {
        id: 'scene-1',
        templateId: 'invalid/template/does/not/exist',
        durationInFrames: 60,
        startFrame: 0
      }
    ]
  }, true, 'TEMPLATE_GATE');

  // Test D - Missing Media
  assertBuild('Test D - Missing Media (Illegal Absolute Path)', {
    id: 'test-d',
    width: 1920,
    height: 1080,
    fps: 30,
    durationInFrames: 60,
    assets: {
      "main": "C:\\Windows\\System32\\foo.mp4"
    },
    scenes: [
      {
        id: 'scene-1',
        templateId: 'scenes/ChaosDesktop',
        durationInFrames: 60,
        startFrame: 0
      }
    ]
  }, true, 'MEDIA_GATE');

  // Test E - Timeline Failure
  assertBuild('Test E - Timeline Failure (Negative Duration)', {
    id: 'test-e',
    width: 1920,
    height: 1080,
    fps: 30,
    durationInFrames: -50,
    scenes: [
      {
        id: 'scene-1',
        templateId: 'scenes/ChaosDesktop',
        durationInFrames: -10,
        startFrame: 0
      }
    ]
  }, true, 'TIMELINE_GATE');

  console.log(`--- TEST RESULTS: ${passed}/${total} PASS ---`);
  if (passed !== total) {
    process.exit(1);
  }
}

runTests();
