import * as fs from 'fs';
import * as path from 'path';

const ROOT_DIR = path.resolve(__dirname, '../../');
const STRATEGY_PATH = path.join(ROOT_DIR, 'ground-truth/phase_16_1_adapter_strategy.json');
const OUTPUT_PATH = path.join(ROOT_DIR, 'ground-truth/phase_16_2_default_evidence.json');

function main() {
  const strategy = JSON.parse(fs.readFileSync(STRATEGY_PATH, 'utf-8'));
  const candidates = strategy.defaultFixCandidates;
  
  const allEvidence: any[] = [];
  
  for (const templateId of candidates) {
    const sourcePath = path.join(ROOT_DIR, `remotion-app/src/templates/${templateId}.tsx`);
    const enginePath = path.join(ROOT_DIR, `remotion-app/src/engine/${templateId}.tsx`);
    const actualPath = fs.existsSync(sourcePath) ? sourcePath : (fs.existsSync(enginePath) ? enginePath : null);
    
    if (actualPath) {
      const sourceCode = fs.readFileSync(actualPath, 'utf-8');
      
      // Look for functional component props like ({ size = 24, color = "red" })
      // Matches ({ ... }) where the content is captured in group 1
      const propsRegex = /\(\s*\{\s*([^}]+)\s*\}\s*(?::\s*[A-Za-z0-9_]+)?\s*\)\s*=>/g;
      
      let match;
      while ((match = propsRegex.exec(sourceCode)) !== null) {
        const propsString = match[1];
        
        // Split by comma, but be careful with strings containing commas (assume simple values)
        const propAssignments = propsString.split(',').map(s => s.trim()).filter(s => s.length > 0);
        
        for (const assignment of propAssignments) {
          const eqIndex = assignment.indexOf('=');
          if (eqIndex > -1) {
            const propName = assignment.substring(0, eqIndex).trim();
            const rawValue = assignment.substring(eqIndex + 1).trim();
            
            let parsedValue: any = undefined;
            if (rawValue === 'true') parsedValue = true;
            else if (rawValue === 'false') parsedValue = false;
            else if (!isNaN(Number(rawValue))) parsedValue = Number(rawValue);
            else if ((rawValue.startsWith('"') && rawValue.endsWith('"')) || (rawValue.startsWith("'") && rawValue.endsWith("'"))) {
              parsedValue = rawValue.substring(1, rawValue.length - 1);
            }
            
            if (parsedValue !== undefined && !allEvidence.find(e => e.prop === propName && e.templateId === templateId)) {
              allEvidence.push({
                templateId,
                prop: propName,
                value: parsedValue,
                source: path.relative(ROOT_DIR, actualPath).replace(/\\/g, '/'),
                sourceLocation: 'AST/Regex Component',
                evidenceType: 'source_default',
                confidence: 'HIGH'
              });
            }
          }
        }
      }
      
      // Also look for Zod schema defaults in schema.ts
      const schemaPath = path.join(path.dirname(actualPath), 'schema.ts');
      if (fs.existsSync(schemaPath)) {
        const schemaCode = fs.readFileSync(schemaPath, 'utf-8');
        // Match: propName: z.something().default('val')
        const zodRegex = /([A-Za-z0-9_]+)\s*:\s*z\..*?\.default\((.*?)\)(?=\s*[,}\n])/g;
        let zMatch;
        while ((zMatch = zodRegex.exec(schemaCode)) !== null) {
          const propName = zMatch[1];
          const rawValue = zMatch[2].trim();
          let parsedValue: any = undefined;
          
          if (rawValue === 'true') parsedValue = true;
          else if (rawValue === 'false') parsedValue = false;
          else if (!isNaN(Number(rawValue))) parsedValue = Number(rawValue);
          else if ((rawValue.startsWith('"') && rawValue.endsWith('"')) || (rawValue.startsWith("'") && rawValue.endsWith("'"))) {
            parsedValue = rawValue.substring(1, rawValue.length - 1);
          }
          
          if (parsedValue !== undefined && !allEvidence.find(e => e.prop === propName && e.templateId === templateId)) {
            allEvidence.push({
              templateId,
              prop: propName,
              value: parsedValue,
              source: path.relative(ROOT_DIR, schemaPath).replace(/\\/g, '/'),
              sourceLocation: 'AST/Regex Zod',
              evidenceType: 'schema_default',
              confidence: 'HIGH'
            });
          }
        }
      }
    }
  }
  
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(allEvidence, null, 2));
  console.log(`Extracted ${allEvidence.length} proven defaults across ${candidates.length} templates.`);
}

main();
