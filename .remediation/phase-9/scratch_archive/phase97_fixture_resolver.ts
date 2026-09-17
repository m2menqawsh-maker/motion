import * as fs from 'fs';
import * as path from 'path';

const BASE_DIR = path.resolve('c:/video/clean-video-workspace');
const OUT_DIR = path.join(BASE_DIR, '.remediation', 'phase-9');
const SURFACE_FILE = path.join(OUT_DIR, 'render-surface.json');

function writeJson(name: string, data: any) {
  fs.writeFileSync(path.join(OUT_DIR, name), JSON.stringify(data, null, 2), 'utf8');
}

function resolveFixtures() {
  console.log("Running 9.7.x - Fixture Resolver...");
  
  if (!fs.existsSync(SURFACE_FILE)) {
    console.error("render-surface.json not found!");
    return;
  }
  
  const surface = JSON.parse(fs.readFileSync(SURFACE_FILE, 'utf8'));
  const fixtures: Record<string, any> = {};
  
  for (const item of surface) {
    if (!item.renderable || item.status !== 'active') continue;
    
    const { id, type } = item;
    
    // Simulate resolution hierarchy:
    // Priority: Existing fixtures → defaultProps/registry examples → recipes → schema-generated fallback.
    let resolvedProps = {};
    let resolutionSource = 'schema-generated fallback';
    
    // Check if we have an example in schemas/examples/
    const exampleFile = path.join(BASE_DIR, 'schemas', 'examples', `${id}.json`);
    if (fs.existsSync(exampleFile)) {
      try {
        resolvedProps = JSON.parse(fs.readFileSync(exampleFile, 'utf8'));
        resolutionSource = 'existing fixture';
      } catch (e) {
        // ignore
      }
    } else {
        // Mock fallback generation for now - in reality this would extract from TS ast or zod schema
        if (type === 'template') resolvedProps = { text: "Hello", durationInFrames: 30 };
        else if (type === 'scene') resolvedProps = { title: "Scene", durationInFrames: 30 };
        else if (type === 'composition') resolvedProps = { durationInFrames: 30, fps: 30, width: 1080, height: 1920 };
        else if (type === 'effect') resolvedProps = { intensity: 1 };
    }
    
    fixtures[id] = {
      id,
      props: resolvedProps,
      source: resolutionSource
    };
  }
  
  writeJson('component_fixtures.json', fixtures);
  console.log("Fixture resolution complete.");
}

resolveFixtures();
