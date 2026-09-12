import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const COMPONENTS_DIR = path.resolve(
  __dirname,
  "../.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components"
);

const OUTPUT_FILE = path.resolve(__dirname, "auto-generated-entries.ts");

interface ExtractedProp {
  name: string;
  type: string;
  description: string;
}

interface ExtractedTemplate {
  id: string;
  props: ExtractedProp[];
}

function parseMarkdownTable(tableContent: string): ExtractedProp[] {
  const lines = tableContent.split("\n").filter((line) => line.trim().startsWith("|"));
  if (lines.length < 3) return []; // Header, separator, data

  const props: ExtractedProp[] = [];
  // Skip first two lines (header + separator)
  for (let i = 2; i < lines.length; i++) {
    const row = lines[i];
    const cols = row.split("|").map((c) => c.trim());
    if (cols.length >= 4) {
      // Assuming typical format: | Name | Type | Default | Description |
      // Or: | Prop | Type | Description |
      const name = cols[1];
      const type = cols[2];
      const desc = cols.length >= 5 ? cols[4] : cols[3];
      
      // Clean up markdown formatting like backticks
      props.push({
        name: name.replace(/`/g, ""),
        type: type.replace(/`/g, ""),
        description: desc
      });
    }
  }
  return props;
}

function extractProps(content: string): ExtractedProp[] {
  const propsMatch = content.match(/## Props([\s\S]*?)(?:##|$)/);
  if (propsMatch && propsMatch[1]) {
    return parseMarkdownTable(propsMatch[1]);
  }
  return [];
}

async function main() {
  if (!fs.existsSync(COMPONENTS_DIR)) {
    console.error(`Directory not found: ${COMPONENTS_DIR}`);
    process.exit(1);
  }

  const files = fs.readdirSync(COMPONENTS_DIR).filter((f) => f.endsWith(".md"));
  const templates: ExtractedTemplate[] = [];

  for (const file of files) {
    if (file === "index.md") continue;

    const id = file.replace(/\.md$/, "");
    const content = fs.readFileSync(path.join(COMPONENTS_DIR, file), "utf-8");
    const props = extractProps(content);
    
    templates.push({ id, props });
  }

  // Generate output file
  let outContent = `// هذا الملف تم توليده آلياً بواسطة docs-extractor.ts\n`;
  outContent += `// استخدمه كمرجع لبناء template-registry.tsx ولا تقم باستيراده مباشرة في الكود النهائي.\n\n`;
  outContent += `export const AUTO_GENERATED_TEMPLATES = [\n`;

  let totalProps = 0;

  for (const t of templates) {
    outContent += `  {\n`;
    outContent += `    id: "${t.id}",\n`;
    outContent += `    props: [\n`;
    for (const p of t.props) {
      outContent += `      { name: "${p.name}", type: "${p.type.replace(/"/g, '\\"')}", description: "${p.description.replace(/"/g, '\\"')}" },\n`;
      totalProps++;
    }
    outContent += `    ]\n`;
    outContent += `  },\n`;
  }
  outContent += `];\n`;

  fs.writeFileSync(OUTPUT_FILE, outContent, "utf-8");
  
  console.log(`استُخرج ${templates.length} قالب، بمتوسط ${(totalProps / (templates.length || 1)).toFixed(1)} props لكل قالب (إجمالي ${totalProps} prop).`);
}

main().catch(console.error);
