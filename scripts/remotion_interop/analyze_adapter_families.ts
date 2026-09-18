import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.join(__dirname, '..');
const REGISTRY_PATH = path.join(ROOT_DIR, 'remotion-app/src/engine/catalog/registry.json');
const OUTPUT_PATH = path.join(ROOT_DIR, 'adapter_family_candidates.json');
const TEMPLATES_ROOT = path.join(ROOT_DIR, 'remotion-app/src');

function analyze() {
  if (!fs.existsSync(REGISTRY_PATH)) {
    console.error('Registry not found');
    process.exit(1);
  }

  const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf-8'));
  const schemas = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'ground-truth/template_prop_schemas.json'), 'utf-8'));
  const results = [];

  for (const t of registry.templates) {
    let candidateFamilies = [];
    const evidence = [];
    let confidence = 'UNKNOWN';
    const blockingReasons = [];

    // Combine capabilities, schemas, and source code
    let contentCaps = t.capabilities?.content || [];
    let mediaCaps = t.capabilities?.media || [];
    let behaviorCaps = t.capabilities?.behavior || [];
    
    // Look at schema
    const schema = schemas[t.templateId] || { required: [], optional: [] };
    const allSchemaProps = [...schema.required, ...schema.optional];

    // Read source code to infer props if schema is missing/empty
    let sourcePath = path.join(TEMPLATES_ROOT, 'templates', t.templateId + '.tsx');
    if (!fs.existsSync(sourcePath)) {
      sourcePath = path.join(TEMPLATES_ROOT, 'templates', t.templateId, 'index.tsx');
    }
    if (!fs.existsSync(sourcePath)) {
      sourcePath = path.join(TEMPLATES_ROOT, 'engine', t.templateId + '.tsx');
    }

    let sourceCode = '';
    if (fs.existsSync(sourcePath)) {
      sourceCode = fs.readFileSync(sourcePath, 'utf-8');
    } else {
      blockingReasons.push('Source code not found for analysis');
    }

    // Heuristics for props
    const hasTextProp = allSchemaProps.includes('text') || sourceCode.includes('text}:') || sourceCode.includes('text,');
    const hasTitleProp = allSchemaProps.includes('title') || sourceCode.includes('title}:') || sourceCode.includes('title,');
    const hasSubtitleProp = allSchemaProps.includes('subtitle') || sourceCode.includes('subtitle}:') || sourceCode.includes('subtitle,');
    const hasImageProp = allSchemaProps.includes('imageUrl') || allSchemaProps.includes('imageSrc') || sourceCode.includes('imageUrl') || sourceCode.includes('<Img');
    const hasVideoProp = allSchemaProps.includes('videoUrl') || allSchemaProps.includes('videoSrc') || sourceCode.includes('<Video');
    const hasAudioProp = allSchemaProps.includes('audioSrc') || sourceCode.includes('<Audio');
    const hasChildrenProp = allSchemaProps.includes('children') || sourceCode.includes('children}:') || sourceCode.includes('children,');

    if (hasTextProp) evidence.push('Source/Schema suggests text prop');
    if (hasTitleProp) evidence.push('Source/Schema suggests title prop');
    if (hasSubtitleProp) evidence.push('Source/Schema suggests subtitle prop');
    if (hasImageProp) evidence.push('Source/Schema suggests image/media prop or Img usage');
    if (hasVideoProp) evidence.push('Source/Schema suggests video prop or Video usage');
    if (hasAudioProp) evidence.push('Source/Schema suggests audio prop or Audio usage');

    // 1. Animated Text Family
    if ((hasTextProp || hasTitleProp || contentCaps.includes('headline')) && !hasImageProp && !hasVideoProp) {
      if (sourceCode.includes('spring') || sourceCode.includes('interpolate') || behaviorCaps.includes('animated')) {
        candidateFamilies.push('animated_text_v1');
        evidence.push('Matched animated_text_v1 profile (text + animation - media)');
      }
    }

    // 2. Image Card / Media Reveal Family
    if ((hasImageProp && !hasVideoProp) && (hasTitleProp || hasTextProp || contentCaps.includes('headline'))) {
      candidateFamilies.push('image_card_v1');
      evidence.push('Matched image_card_v1 profile (image + text)');
    }

    // 3. Video Player Family
    if (hasVideoProp) {
      candidateFamilies.push('video_player_v1');
      evidence.push('Matched video_player_v1 profile (video)');
    }

    // 4. UI / Notification Family
    if ((hasTitleProp && hasSubtitleProp) || sourceCode.toLowerCase().includes('notification') || sourceCode.toLowerCase().includes('toast')) {
      candidateFamilies.push('ui_notification_v1');
      evidence.push('Matched ui_notification_v1 profile (title + subtitle or UI naming)');
    }

    // 5. Container / Split Screen Family
    if (hasChildrenProp || sourceCode.toLowerCase().includes('split') || sourceCode.toLowerCase().includes('grid')) {
      candidateFamilies.push('container_v1');
      evidence.push('Matched container_v1 profile (children or layout naming)');
    }

    // Confidence
    if (candidateFamilies.length > 0) {
      if (allSchemaProps.length > 0) confidence = 'HIGH';
      else confidence = 'MEDIUM'; // Relied on source code heuristics
    } else {
      confidence = 'UNKNOWN';
    }

    if (t.assets.health === 'BROKEN') {
      blockingReasons.push('DEPENDENCY_BLOCKED');
    }
    if (candidateFamilies.length === 0) {
      blockingReasons.push('NO_FAMILY_MATCH');
    }

    results.push({
      templateId: t.templateId,
      candidateFamilies,
      evidence,
      confidence,
      blockingReasons
    });
  }

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(results, null, 2));
  console.log(`Audited ${results.length} templates -> ${OUTPUT_PATH}`);
}

analyze();
