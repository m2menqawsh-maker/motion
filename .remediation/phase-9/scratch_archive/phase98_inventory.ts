import * as fs from 'fs';
import * as path from 'path';

const BASE_DIR = path.resolve('c:/video/clean-video-workspace');
const OUT_DIR = path.join(BASE_DIR, '.remediation', 'phase-9');

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function writeJson(name: string, data: any) {
  fs.writeFileSync(path.join(OUT_DIR, name), JSON.stringify(data, null, 2), 'utf8');
}

function walk(dir: string, fileList: string[] = []) {
  if (!fs.existsSync(dir)) return fileList;
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      walk(filePath, fileList);
    } else {
      fileList.push(filePath);
    }
  }
  return fileList;
}

const MEDIA_EXTS = ['.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v', '.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.svg', '.ttf', '.otf', '.woff', '.woff2'];

function getCategory(ext: string) {
  if (['.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v'].includes(ext)) return 'video';
  if (['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'].includes(ext)) return 'audio';
  if (['.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif'].includes(ext)) return 'image';
  if (ext === '.svg') return 'svg';
  if (['.ttf', '.otf', '.woff', '.woff2'].includes(ext)) return 'font';
  return 'unknown';
}

function getLifecycle(p: string) {
  if (p.includes('assets/incoming')) return 'incoming';
  if (p.includes('assets/processing')) return 'processing';
  if (p.includes('assets/ready')) return 'ready';
  if (p.includes('assets/cache')) return 'cache';
  if (p.includes('public')) return 'public';
  if (p.includes('fixtures') || p.includes('examples') || p.includes('__tests__')) return 'fixture';
  if (p.includes('archive')) return 'historical';
  return 'unknown'; // or generated, etc.
}

function runInventory() {
  console.log("Running 9.8.1 - Asset Inventory Discovery...");
  const surface = [];
  
  const searchDirs = ['assets', 'public', 'remotion-app/public', 'templates', 'recipes', 'registry', 'ground-truth', 'scripts', 'api'];
  
  const allFiles: string[] = [];
  for (const d of searchDirs) {
    const fullPath = path.join(BASE_DIR, d);
    walk(fullPath, allFiles);
  }
  
  const mediaTypeIntegrity = {
    mismatches: 0,
    details: [] as any[]
  };

  for (const f of allFiles) {
    const ext = path.extname(f).toLowerCase();
    if (!MEDIA_EXTS.includes(ext) && !f.endsWith('.json')) continue; // JSON might be metadata
    
    // Ignore non-media json
    if (ext === '.json' && !f.includes('assets')) continue;
    
    const rel = path.relative(BASE_DIR, f).replace(/\\/g, '/');
    const category = ext === '.json' ? 'metadata' : getCategory(ext);
    const lifecycle = getLifecycle(rel);
    
    // Simplistic MIME spoofing check for PNG and JPG for demonstration in inventory
    if (category === 'image') {
       try {
         const buffer = Buffer.alloc(4);
         const fd = fs.openSync(f, 'r');
         fs.readSync(fd, buffer, 0, 4, 0);
         fs.closeSync(fd);
         
         const isPng = buffer[0] === 0x89 && buffer[1] === 0x50 && buffer[2] === 0x4E && buffer[3] === 0x47;
         const isJpg = buffer[0] === 0xFF && buffer[1] === 0xD8 && buffer[2] === 0xFF;
         
         if (ext === '.png' && !isPng) {
           mediaTypeIntegrity.mismatches++;
           mediaTypeIntegrity.details.push({ path: rel, extension: ext, detected: 'unknown/not_png' });
         }
         if ((ext === '.jpg' || ext === '.jpeg') && !isJpg) {
           mediaTypeIntegrity.mismatches++;
           mediaTypeIntegrity.details.push({ path: rel, extension: ext, detected: 'unknown/not_jpg' });
         }
       } catch (e) {}
    }

    surface.push({
      path: rel,
      category,
      lifecycle,
      production_referenced: false, // Updated by phase98_reference_graph
      runtime_reachable: lifecycle === 'ready' || lifecycle === 'public',
      source: 'filesystem',
      status: 'active',
      evidence: ["Found in filesystem"]
    });
  }
  
  writeJson('asset-surface.json', surface);
  writeJson('media-type-integrity.json', mediaTypeIntegrity);
  
  console.log(`Phase 9.8 Inventory Complete. Found ${surface.length} assets.`);
}

runInventory();
