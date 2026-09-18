import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const SCHEMAS_PATH = path.join(ROOT_DIR, 'ground-truth/template_prop_schemas.json');
const CONTRACTS_PATH = path.join(ROOT_DIR, 'ground-truth/template_contracts.json');

const CANDIDATES = [
  'elements/typography/blur-reveal/BlurReveal',
  'elements/typography/rgb-glitch-text/RgbGlitchText',
  'elements/typography/tracking-in/TrackingIn',
  'elements/typography/word-stagger/WordStagger'
];

function patch() {
  const schemas = JSON.parse(fs.readFileSync(SCHEMAS_PATH, 'utf-8'));
  const contracts = JSON.parse(fs.readFileSync(CONTRACTS_PATH, 'utf-8'));

  for (const id of CANDIDATES) {
    // 1. Patch schema
    schemas[id] = {
      required: [],
      optional: ['text', 'delay', 'duration', 'color', 'fontSize', 'fontFamily', 'align'],
      defaults: {
        text: "Onda",
        delay: 0,
        duration: 30
      }
    };

    // 2. Patch contract
    const contract = contracts.templates.find((t: any) => t.id === id);
    if (contract) {
      contract.props = {
        text: { type: 'string' },
        delay: { type: 'number' },
        duration: { type: 'number' },
        color: { type: 'string' },
        fontSize: { type: 'number' },
        fontFamily: { type: 'string' },
        align: { type: 'string' }
      };
      contract.schema = {
        status: 'DEFINED',
        source: 'manual_patch_phase14'
      };
      contract.safe_mock = {
        text: "Onda",
        delay: 0,
        duration: 30
      };
      contract.mock_status = 'SAFE';
      contract.runtime_risk = 'MODERATE';
    }
  }

  fs.writeFileSync(SCHEMAS_PATH, JSON.stringify(schemas, null, 2));
  fs.writeFileSync(CONTRACTS_PATH, JSON.stringify(contracts, null, 2));
  console.log('Patched schemas and contracts for candidates.');
}

patch();
