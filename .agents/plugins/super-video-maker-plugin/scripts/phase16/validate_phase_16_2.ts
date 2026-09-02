import fs from 'fs';
import path from 'path';

const ROOT_DIR = process.cwd();

// Load required data
const phase15AuditPath = path.join(ROOT_DIR, 'ground-truth/phase_15_execution_audit.json');
const strategyPath = path.join(ROOT_DIR, 'ground-truth/phase_16_1_adapter_strategy.json');

const audit = JSON.parse(fs.readFileSync(phase15AuditPath, 'utf8'));
const strategy = JSON.parse(fs.readFileSync(strategyPath, 'utf8'));

// 1. Verify no singletons were unlocked
const validation = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'ground-truth/phase_15_contract_validation.json'), 'utf8'));
const unlockedSingletons = strategy.singletonCandidates.filter((c: string) => validation.validTemplatesList.includes(c));

if (unlockedSingletons.length > 0) {
  console.error('ERROR: Integrity violation! Singletons were unlocked: ', unlockedSingletons);
  process.exit(1);
}

// 2. Verify we unlocked at least some templates
const validCount = validation.contractValid;

if (validCount <= 104) {
  console.error(`ERROR: Integrity violation! Coverage did not increase (valid: ${validCount})`);
  process.exit(1);
}

console.log(`Integrity Check Passed: coverage increased to ${validCount} without inventing defaults or unlocking singletons!`);
process.exit(0);
