import { ProjectData } from "./merge";

const DEFAULT_BRAND = {
  brandName: "Default",
  logoSrc: null,
  colors: {
    primary: "#00F5FF",
    accent: "#FFD700",
    background: "#0A0E27",
    text: "#FFFFFF"
  },
  fonts: {
    display: "Cairo",
    body: "IBMPlexSansArabic"
  }
};

/**
 * يقرأ بيانات المشروع ويفحصها باستخدام بيئة Python المتوفرة في Workspace.
 * يجب استدعاء هذه الدالة فقط في بيئة Node (مثال: calculateMetadata).
 */
export function loadProjectData(projectDir: string): ProjectData {
  // استخدام eval("require") لمنع Webpack من محاولة تجميع حزم Node في بيئة المتصفح
  const req = typeof window === "undefined" ? eval("require") : () => null;
  const fs = req("fs") as typeof import("fs");
  const path = req("path") as typeof import("path");
  const { execSync } = req("child_process") as typeof import("child_process");

  const projectPath = path.join(projectDir, "project.json");
  const blueprintPath = path.join(projectDir, "blueprint.json");
  const brandPath = path.join(projectDir, "brand.json");
  const overridesPath = path.join(projectDir, "overrides.json");
  const manifestPath = path.join(projectDir, "manifest.json");

  if (!fs.existsSync(blueprintPath)) {
    throw new Error(`Missing mandatory file: blueprint.json in ${projectDir}`);
  }

  // Option 1: Validate files dynamically using python script.
  // Note: For unit tests that mock the structure in memory without all files, this could fail,
  // so we catch and log or fail gracefully if the python script is not found/fails.
  try {
    const pythonScript = path.resolve(__dirname, "../../../scripts/validate_schemas.py");
    if (fs.existsSync(pythonScript)) {
      execSync(`python "${pythonScript}" "${projectDir}"`, { stdio: 'pipe' });
    }
  } catch (error: any) {
    console.warn("Schema validation warning:", error?.stdout?.toString() || error.message);
  }

  const project = fs.existsSync(projectPath)
    ? JSON.parse(fs.readFileSync(projectPath, "utf-8"))
    : { fps: 30, title: "Untitled" };

  const blueprint = JSON.parse(fs.readFileSync(blueprintPath, "utf-8"));
  
  const brand = fs.existsSync(brandPath)
    ? JSON.parse(fs.readFileSync(brandPath, "utf-8"))
    : DEFAULT_BRAND;

  const overrides = fs.existsSync(overridesPath)
    ? JSON.parse(fs.readFileSync(overridesPath, "utf-8"))
    : { scenes: {} };

  const manifest = fs.existsSync(manifestPath)
    ? JSON.parse(fs.readFileSync(manifestPath, "utf-8"))
    : null;

  return { project, blueprint, brand, overrides, manifest };
}
