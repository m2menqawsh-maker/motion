import { describe, it, expect } from "vitest";
import { mergeScene, mergeProject, BlueprintScene, SceneOverride, ProjectData } from "../build/src/merge";
import { loadProjectData } from "../build/src/loadProjectData";
import { BrandKit } from "../contracts/brand";
import { TemplateEntry } from "../registry/types";
import * as fs from "fs";
import * as path from "path";

// مسار وهمي للتجارب
const MOCK_DIR = path.resolve(__dirname, "mock_project");

describe("Merge & Load Project Data Tests", () => {
  const dummyBrand: BrandKit = {
    brandName: "Dummy",
    logoSrc: null,
    colors: { primary: "#ff0000", accent: "#00ff00", background: "#0000ff", text: "#fff" },
    fonts: { display: "Cairo", body: "Inter" }
  };

  const dummyRegistryEntry = {
    id: "test",
    defaults: { text: "default text", color: "#000" },
    schema: {}
  } as TemplateEntry;

  it("1. defaults تُطبق عند غياب props", () => {
    const scene: BlueprintScene = { scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30 };
    const merged = mergeScene(scene, dummyRegistryEntry, dummyBrand);
    expect(merged.surface.text).toBe("default text");
    expect(merged.surface.color).toBe("#000");
  });

  it("2. props تتغلب على defaults", () => {
    const scene: BlueprintScene = { 
      scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30,
      props: { text: "props text" }
    };
    const merged = mergeScene(scene, dummyRegistryEntry, dummyBrand);
    expect(merged.surface.text).toBe("props text");
    expect(merged.surface.color).toBe("#000"); // From defaults
  });

  it("3. overrides تتغلب على props", () => {
    const scene: BlueprintScene = { 
      scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30,
      props: { text: "props text" }
    };
    const override: SceneOverride = { props: { text: "overridden text" } };
    const merged = mergeScene(scene, dummyRegistryEntry, dummyBrand, override);
    expect(merged.surface.text).toBe("overridden text");
  });

  it("4. 'brand.primary' يُحل إلى hex النهائي", () => {
    const scene: BlueprintScene = { 
      scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30,
      props: { color: "brand.primary" }
    };
    const merged = mergeScene(scene, dummyRegistryEntry, dummyBrand);
    expect(merged.surface.color).toBe("#ff0000");
  });

  it("5. token غير معروف يبقى literal بدون كراش", () => {
    const scene: BlueprintScene = { 
      scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30,
      props: { color: "brand.unknown" }
    };
    const merged = mergeScene(scene, dummyRegistryEntry, dummyBrand);
    expect(merged.surface.color).toBe("brand.unknown");
  });

  it("6. overrides.timing يستبدل startFrame/durationFrames", () => {
    const scene: BlueprintScene = { scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30 };
    const override: SceneOverride = { timing: { startFrame: 10, durationFrames: 50 } };
    const merged = mergeScene(scene, dummyRegistryEntry, dummyBrand, override);
    expect(merged.startFrame).toBe(10);
    expect(merged.durationFrames).toBe(50);
  });

  it("7. styleOverride بمفتاح مرفوض يُحذف ولا يكسر الدمج", () => {
    const scene: BlueprintScene = { scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30 };
    const override: SceneOverride = { props: { styleOverride: { padding: "10px", zIndex: 99 } } };
    const merged = mergeScene(scene, dummyRegistryEntry, dummyBrand, override);
    expect(merged.surface.styleOverride).toHaveProperty("padding", "10px");
    expect(merged.surface.styleOverride).not.toHaveProperty("zIndex");
  });

  it("8. غياب brand.json → default brand بدون كراش", () => {
    // Create dummy blueprint to mock loading
    if (!fs.existsSync(MOCK_DIR)) fs.mkdirSync(MOCK_DIR, { recursive: true });
    fs.writeFileSync(path.join(MOCK_DIR, "project.json"), JSON.stringify({ fps: 30, title: "Test" }));
    fs.writeFileSync(path.join(MOCK_DIR, "blueprint.json"), JSON.stringify({ scenes: [] }));
    
    // No brand.json written
    const data = loadProjectData(MOCK_DIR);
    expect(data.brand).toBeDefined();
    expect(data.brand.brandName).toBe("Default");
    expect(data.brand.colors.primary).toBe("#00F5FF"); // The required default
    
    // Cleanup
    fs.rmSync(MOCK_DIR, { recursive: true, force: true });
  });

  it("9. المشاهد مرتبة تصاعدياً في المخرج", () => {
    const data: ProjectData = {
      project: { fps: 30, title: "Sort Test" },
      brand: dummyBrand,
      blueprint: {
        scenes: [
          { scene_id: "s2", template: "test", startFrame: 100, durationFrames: 30 },
          { scene_id: "s1", template: "test", startFrame: 0, durationFrames: 30 },
        ]
      }
    };
    const getEntry = () => dummyRegistryEntry;
    const merged = mergeProject(data, getEntry);
    expect(merged.scenes[0].scene_id).toBe("s1");
    expect(merged.scenes[1].scene_id).toBe("s2");
    expect(merged.totalDurationFrames).toBe(130); // 100 + 30
  });

  it("10. غياب blueprint.json → خطأ واضح (رسالة تحتوي 'blueprint')", () => {
    if (!fs.existsSync(MOCK_DIR)) fs.mkdirSync(MOCK_DIR, { recursive: true });
    fs.writeFileSync(path.join(MOCK_DIR, "project.json"), JSON.stringify({ fps: 30, title: "Test" }));
    // Explicitly do NOT write blueprint.json
    
    expect(() => loadProjectData(MOCK_DIR)).toThrowError(/blueprint/i);
    
    // Cleanup
    fs.rmSync(MOCK_DIR, { recursive: true, force: true });
  });
});
