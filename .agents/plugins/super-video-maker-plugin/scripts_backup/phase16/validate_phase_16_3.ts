import fs from 'fs';
import path from 'path';

const ROOT_DIR = process.cwd();

const audit162Path = path.join(ROOT_DIR, 'ground-truth/phase_15_contract_validation.json');
const audit163Path = path.join(ROOT_DIR, 'ground-truth/phase_15_execution_audit.json');

const audit162 = JSON.parse(fs.readFileSync(audit162Path, 'utf8'));
const audit163 = JSON.parse(fs.readFileSync(audit163Path, 'utf8'));

// 1. All 127 Phase 16.2 supported templates remain supported
const valid163Templates = audit163.auditResults
  .filter((r: any) => r.executionClassification === 'CONTRACT_VALID' || r.executionClassification === 'STATIC_ZERO_PROP')
  .map((r: any) => r.templateId);

const missingFrom162 = audit162.validTemplatesList.filter((t: string) => !valid163Templates.includes(t));
if (missingFrom162.length > 0) {
  console.error('ERROR: Phase 16.2 supported templates regressed: ', missingFrom162);
  process.exit(1);
}

// 2. adapter integrity
const socialClip1 = audit163.auditResults.find((r: any) => r.templateId === 'scenes/social/SocialClip');
const socialClip2 = audit163.auditResults.find((r: any) => r.templateId === 'scenes/social/social-clip/index');

if (socialClip1?.adapterCapability !== 'social_captions_v1') {
  console.error('ERROR: SocialClip adapterCapability is not social_captions_v1');
  process.exit(1);
}
if (socialClip2?.adapterCapability !== 'social_captions_v1') {
  console.error('ERROR: social-clip/index adapterCapability is not social_captions_v1');
  process.exit(1);
}

// 3. No singleton was unlocked
const singletons = [
  'primitives/app-ui/AppShell',
  'audio/AudioManager',
  'camera/CameraRig'
];

for (const singleton of singletons) {
  const result = audit163.auditResults.find((r: any) => r.templateId === singleton);
  if (result && (result.executionClassification === 'CONTRACT_VALID' || result.executionClassification === 'STATIC_ZERO_PROP')) {
    console.error(`ERROR: Singleton was unlocked: ${singleton}`);
    process.exit(1);
  }
}

console.log("Phase 16.3 validation passed!");
