import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';
import { buildVideo } from '../remotion-app/src/engine/orchestration/BuildEngine';
import { generateCompositionRoot } from '../remotion-app/src/engine/orchestration/SceneComposer';
import { VideoSpec } from '../remotion-app/src/engine/orchestration/types';
import { CreativeCompiler } from '../remotion-app/src/engine/planning/Compiler';

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    specPath: '',
    creativePath: '',
    dryRun: false,
    render: false,
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--spec' && args[i + 1]) {
      options.specPath = args[i + 1];
      i++;
    } else if (args[i] === '--creative' && args[i + 1]) {
      options.creativePath = args[i + 1];
      i++;
    } else if (args[i] === '--dry-run') {
      options.dryRun = true;
    } else if (args[i] === '--render') {
      options.render = true;
    }
  }

  return options;
}

function main() {
  const options = parseArgs();
  if (!options.specPath && !options.creativePath) {
    console.error('Error: --spec <path> or --creative <path> is required.');
    process.exit(1);
  }

  let spec: VideoSpec;

  if (options.creativePath) {
    const absoluteCreativePath = path.resolve(process.cwd(), options.creativePath);
    if (!fs.existsSync(absoluteCreativePath)) {
      console.error(`Error: Creative spec file not found at ${absoluteCreativePath}`);
      process.exit(1);
    }

    let creativeSpec;
    try {
      creativeSpec = JSON.parse(fs.readFileSync(absoluteCreativePath, 'utf-8'));
    } catch (e) {
      console.error('Error: Failed to parse creative spec file as JSON.');
      process.exit(1);
    }

    console.log('Compiling Creative Specification...');
    const compileResult = CreativeCompiler.compile(creativeSpec);
    if (!compileResult.success || !compileResult.videoSpec) {
      console.error('Error: Compilation failed.');
      console.error(JSON.stringify(compileResult.errors, null, 2));
      process.exit(1);
    }
    spec = compileResult.videoSpec;
    console.log('Compilation passed.');
  } else {
    const absoluteSpecPath = path.resolve(process.cwd(), options.specPath);
    if (!fs.existsSync(absoluteSpecPath)) {
      console.error(`Error: Spec file not found at ${absoluteSpecPath}`);
      process.exit(1);
    }

    try {
      spec = JSON.parse(fs.readFileSync(absoluteSpecPath, 'utf-8'));
    } catch (e) {
      console.error('Error: Failed to parse spec file as JSON.');
      process.exit(1);
    }
  }

  console.log('Validating Video Specification...');
  const result = buildVideo(spec, { dryRun: options.dryRun });

  if (options.dryRun) {
    console.log('\n================================');
    console.log('       VIDEO BUILD PLAN');
    console.log('================================');
    console.log(`Resolution: ${result.plan.resolution.width}x${result.plan.resolution.height}`);
    console.log(`FPS: ${result.plan.fps}`);
    console.log(`\nScenes:`);
    result.plan.scenes.forEach((s, idx) => {
      console.log(`${String(idx + 1).padStart(2, '0')}  ${s.spec.templateId.padEnd(25)} ${s.spec.startFrame} → ${s.spec.startFrame + s.spec.durationInFrames}`);
    });
    console.log(`\nTemplates:`);
    result.plan.scenes.forEach((s) => {
      console.log(`${s.spec.templateId.padEnd(25)} ${s.status}`);
    });
    console.log(`\nAssets:`);
    console.log(`${result.plan.assets.total} resolved`);
    console.log(`${result.plan.assets.missing} missing`);
    console.log(`\nDuration:\n${result.plan.duration} frames`);
    
    console.log(`\nSTATUS:`);
    console.log(result.success ? 'READY_FOR_RENDER' : 'BUILD_BLOCKED');

    if (!result.success) {
      console.log('\nERRORS:');
      console.log(JSON.stringify(result.errors, null, 2));
    }
    if (result.warnings.length > 0) {
      console.log('\nWARNINGS:');
      console.log(JSON.stringify(result.warnings, null, 2));
    }
    process.exit(result.success ? 0 : 1);
  }

  if (!result.success) {
    console.error('\nBuild failed during validation gates:');
    console.error(JSON.stringify(result.errors, null, 2));
    process.exit(1);
  }

  console.log('Validation passed. Generating composition...');
  const rootPath = generateCompositionRoot(result);

  if (options.render) {
    console.log(`\nStarting Remotion render from ${rootPath}...`);
    try {
      const renderCmd = `npx remotion render ${rootPath} OrchestratedVideo out/orchestrated.mp4 --gl=angle`;
      execSync(renderCmd, { stdio: 'inherit', cwd: path.join(__dirname, '../remotion-app') });
      console.log('\nRender Complete!');
    } catch (e) {
      console.error('\nRender failed!');
      process.exit(1);
    }
  } else {
    console.log('\nBuild ready! Pass --render to execute.');
  }
}

main();

