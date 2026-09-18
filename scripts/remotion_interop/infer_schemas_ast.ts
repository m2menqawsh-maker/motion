import { Project, SyntaxKind, ObjectLiteralExpression, PropertyAssignment, SourceFile } from "ts-morph";
import * as fs from "fs";
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const project = new Project({
  tsConfigFilePath: path.join(__dirname, "tsconfig.json"),
});

const registryPath = path.resolve(process.cwd(), "registry/template-registry.tsx");
const registryFile = project.addSourceFileAtPath(registryPath);

// Function to infer type from prop name
function inferPropTypeAndDefault(propName: string): { type: string; defaultVal: any; labelEn: string; labelAr: string } {
  const lower = propName.toLowerCase();
  if (lower.includes("color") || lower.includes("background")) return { type: "color", defaultVal: "#ffffff", labelEn: propName, labelAr: "لون" };
  if (lower.includes("text") || lower.includes("title") || lower.includes("subtitle")) return { type: "text", defaultVal: "Sample Text", labelEn: propName, labelAr: "نص" };
  if (lower.includes("size") || lower.includes("width") || lower.includes("height") || lower.includes("duration") || lower.includes("delay")) {
    let def = 100;
    if (lower.includes("duration")) def = 30;
    if (lower.includes("size")) def = 40;
    return { type: "number", defaultVal: def, labelEn: propName, labelAr: "رقم" };
  }
  if (lower.includes("font")) return { type: "fontKey", defaultVal: "Inter", labelEn: "Font", labelAr: "الخط" };
  if (lower.includes("animation")) return { type: "animation", defaultVal: "none", labelEn: "Animation", labelAr: "حركة" };
  return { type: "text", defaultVal: "", labelEn: propName, labelAr: propName };
}

// Global dictionary to hold inferred schemas
const inferredSchemas: Record<string, any> = {};
const inferredDefaults: Record<string, any> = {};

async function run() {
  console.log("Analyzing template registry...");
  
  const registryDecl = registryFile.getVariableDeclaration("CANONICAL_TEMPLATE_REGISTRY");
  if (!registryDecl) {
    console.error("Could not find CANONICAL_TEMPLATE_REGISTRY");
    return;
  }
  
  const initializer = registryDecl.getInitializerIfKind(SyntaxKind.ObjectLiteralExpression);
  if (!initializer) {
    console.error("CANONICAL_TEMPLATE_REGISTRY is not an object literal");
    return;
  }
  
  let modifiedCount = 0;
  const entries = initializer.getProperties();
  
  for (const entry of entries) {
    if (entry.getKind() !== SyntaxKind.PropertyAssignment) continue;
    const propAssignment = entry as PropertyAssignment;
    const templateObj = propAssignment.getInitializerIfKind(SyntaxKind.ObjectLiteralExpression);
    if (!templateObj) continue;
    
    const idProp = templateObj.getProperty("id") as PropertyAssignment;
    const compProp = templateObj.getProperty("component") as PropertyAssignment;
    
    if (!idProp || !compProp) continue;
    
    const templateId = idProp.getInitializer()?.getText().replace(/["']/g, "") || "unknown";
    const compName = compProp.getInitializer()?.getText();
    
    if (!compName) continue;
    
    // Find import for this component
    const imports = registryFile.getImportDeclarations();
    let wrapperFilePath = "";
    for (const imp of imports) {
      const namedImports = imp.getNamedImports();
      if (namedImports.some(n => n.getName() === compName)) {
        const moduleSpec = imp.getModuleSpecifierValue();
        wrapperFilePath = path.resolve(path.dirname(registryPath), moduleSpec + (moduleSpec.endsWith(".tsx") ? "" : ".tsx"));
        // fallback to .ts if .tsx doesn't exist
        if (!fs.existsSync(wrapperFilePath)) wrapperFilePath = wrapperFilePath.replace(".tsx", ".ts");
        break;
      }
    }
    
    let schemaProps = new Set<string>();
    
    if (fs.existsSync(wrapperFilePath)) {
      const fileText = fs.readFileSync(wrapperFilePath, "utf-8");
      // Use AST or regex to find surface?.prop or content?.prop
      const surfaceMatches = fileText.matchAll(/surface\?\.([a-zA-Z0-9_]+)/g);
      for (const m of surfaceMatches) schemaProps.add(m[1]);
      
      const contentMatches = fileText.matchAll(/content\?\.([a-zA-Z0-9_]+)/g);
      // For content, usually 'text' or 'lines' or similar
      for (const m of contentMatches) schemaProps.add(m[1]);
      
      // Look for inner imports (compositions)
      const innerImports = fileText.matchAll(/from [\'"]@\/compositions\/([^\'"]+)[\'"]/g);
      for (const imp of innerImports) {
        const innerPath = path.resolve(process.cwd(), "remotion-app/src/compositions", imp[1], "index.tsx");
        if (fs.existsSync(innerPath)) {
          const innerCode = fs.readFileSync(innerPath, "utf-8");
          const zMatch = innerCode.match(/z\.object\({([^}]+)}\)/);
          if (zMatch) {
             const zProps = zMatch[1].matchAll(/([a-zA-Z0-9_]+)\s*:/g);
             for (const p of zProps) schemaProps.add(p[1]);
          }
        }
      }
    } else {
      console.warn(`Wrapper file not found for ${compName} at ${wrapperFilePath}`);
    }
    
    // Generate Schema Object
    if (schemaProps.size > 0) {
      let schemaObjStr = "{\n";
      let defaultsObjStr = "{\n";
      for (const prop of schemaProps) {
        // Skip common functions or ignored props
        if (prop === "map" || prop === "join" || prop === "length") continue;
        
        const inferred = inferPropTypeAndDefault(prop);
        schemaObjStr += `      "${prop}": { type: "${inferred.type}", label: { ar: "${inferred.labelAr}", en: "${inferred.labelEn}" }, default: ${JSON.stringify(inferred.defaultVal)} },\n`;
        defaultsObjStr += `      "${prop}": ${JSON.stringify(inferred.defaultVal)},\n`;
      }
      schemaObjStr += "    }";
      defaultsObjStr += "    }";
      
      // Replace in the TS file
      const schemaPropNode = templateObj.getProperty("schema") as PropertyAssignment;
      const defaultsPropNode = templateObj.getProperty("defaults") as PropertyAssignment;
      
      if (schemaPropNode) {
        schemaPropNode.setInitializer(schemaObjStr);
      }
      if (defaultsPropNode) {
        defaultsPropNode.setInitializer(defaultsObjStr);
      }
      modifiedCount++;
      console.log(`Updated schema for: ${templateId} with ${schemaProps.size} fields.`);
    } else {
      console.log(`No fields extracted for: ${templateId} (Schema remains {})`);
    }
  }
  
  registryFile.saveSync();
  console.log(`Successfully updated ${modifiedCount} templates!`);
}

run().catch(console.error);
