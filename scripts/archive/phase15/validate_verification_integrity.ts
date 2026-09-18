import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const REGISTRY_PATH = path.join(ROOT_DIR, 'remotion-app/src/engine/catalog/registry.json');
const VALIDATION_PATH = path.join(ROOT_DIR, 'ground-truth/phase_15_contract_validation.json');
const COHORTS_PATH = path.join(ROOT_DIR, 'ground-truth/phase_15_execution_cohorts.json');

function main() {
  const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf-8')).templates;
  const validation = JSON.parse(fs.readFileSync(VALIDATION_PATH, 'utf-8'));
  const cohorts = JSON.parse(fs.readFileSync(COHORTS_PATH, 'utf-8'));
  
  const validContracts = new Set(validation.validTemplatesList);
  
  const cohortTemplates = new Set();
  cohorts.forEach((c: any) => c.memberTemplates.forEach((t: string) => cohortTemplates.add(t)));

  let hasErrors = false;

  console.log('Running Integrity Assertions...\n');

  for (const t of registry) {
    const { templateId, executionEligibility, verificationStatus } = t;

    // Assertion 1: INDIVIDUAL_RENDER_VERIFIED must be FULLY_SUPPORTED
    if (verificationStatus === 'INDIVIDUAL_RENDER_VERIFIED' && executionEligibility !== 'FULLY_SUPPORTED') {
      console.error(`ERROR: ${templateId} is INDIVIDUAL_RENDER_VERIFIED but executionEligibility is ${executionEligibility}`);
      hasErrors = true;
    }

    // Assertion 2: COHORT_RENDER_VERIFIED must belong to a valid execution cohort
    if (verificationStatus === 'COHORT_RENDER_VERIFIED' && !cohortTemplates.has(templateId)) {
      console.error(`ERROR: ${templateId} is COHORT_RENDER_VERIFIED but not in any execution cohort`);
      hasErrors = true;
    }

    // Assertion 3: FULLY_SUPPORTED must have CONTRACT_VERIFIED (or equivalent evidence)
    if (executionEligibility === 'FULLY_SUPPORTED' && !validContracts.has(templateId)) {
      console.error(`ERROR: ${templateId} is FULLY_SUPPORTED but not contract-verified`);
      hasErrors = true;
    }

    // Assertion 4: BLOCKED cannot be FULLY_SUPPORTED
    if (verificationStatus === 'BLOCKED' && executionEligibility === 'FULLY_SUPPORTED') {
      console.error(`ERROR: ${templateId} is BLOCKED but executionEligibility is FULLY_SUPPORTED`);
      hasErrors = true;
    }

    // Assertion 5: Exactly one executionEligibility state
    const validEligibilities = ['FULLY_SUPPORTED', 'PARTIALLY_SUPPORTED', 'CATALOG_ONLY', 'BROKEN', 'UNKNOWN'];
    if (!validEligibilities.includes(executionEligibility)) {
      console.error(`ERROR: ${templateId} has invalid executionEligibility: ${executionEligibility}`);
      hasErrors = true;
    }
    
    // Ensure verification states are not used as eligibility states
    const invalidEligibilities = ['CONTRACT_VERIFIED', 'COHORT_RENDER_VERIFIED', 'INDIVIDUAL_RENDER_VERIFIED', 'BLOCKED'];
    if (invalidEligibilities.includes(executionEligibility)) {
      console.error(`ERROR: ${templateId} is using a verification state as executionEligibility: ${executionEligibility}`);
      hasErrors = true;
    }
  }

  if (hasErrors) {
    console.log('\nIntegrity Check Failed.');
    process.exit(1);
  } else {
    console.log('All integrity assertions passed.');
  }
}

main();
