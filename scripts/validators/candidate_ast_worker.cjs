/**
 * scripts/validators/candidate_ast_worker.js
 * ==========================================
 * Deterministic AST analysis and TypeScript compiler worker for TemplateCandidate (S28-07B).
 *
 * Guarantees:
 * - Uses ts-morph for exact TypeScript AST parsing and compiler diagnostics.
 * - Operates entirely in-memory; ZERO writes to canonical template directories.
 * - Extracts exact imports, exports, call expressions, and type diagnostics.
 * - Returns structured JSON to stdout for consumption by Python Static Validation Gates.
 */

const fs = require('fs');
const path = require('path');
const { Project, SyntaxKind } = require('ts-morph');

// ─── Machine-Readable Policies ───────────────────────────────────────────────

const FORBIDDEN_SECURITY_MODULES = new Set([
  'fs', 'node:fs', 'fs/promises', 'node:fs/promises',
  'child_process', 'node:child_process',
  'net', 'node:net',
  'tls', 'node:tls',
  'http', 'node:http',
  'https', 'node:https',
  'dgram', 'node:dgram',
  'dns', 'node:dns',
  'worker_threads', 'node:worker_threads',
  'cluster', 'node:cluster',
  'vm', 'node:vm',
  'v8', 'node:v8',
  'repl', 'node:repl',
  'os', 'node:os',
  'axios', 'node-fetch', 'got', 'needle', 'superagent', 'request',
  'ws', 'socket.io',
]);

const FORBIDDEN_DYNAMIC_CALLS = new Set([
  'eval',
  'Function',
  'exec',
  'spawn',
  'execSync',
  'spawnSync',
  'fork',
]);

const NODE_SPECIFIC_APIS = new Set([
  'process.exit',
  'process.kill',
  'process.abort',
  '__dirname',
  '__filename',
]);

const SENSITIVE_ENV_KEYWORDS = [
  'KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'AUTH', 'CREDENTIAL', 'PRIVATE', 'API'
];

const RAW_FS_REGEX = /(?:^\/etc\/|^\/tmp\/|^\/var\/|^[A-Za-z]:\\|^file:\/\/)/;

// ─── Main Worker Logic ────────────────────────────────────────────────────────

function analyze(inputJson) {
  const { source_code, dependencies = [], skip_tsc = false } = inputJson;
  const declaredDeps = new Set(dependencies.map(d => d.split('@')[0].trim()));

  const result = {
    success: true,
    static_code: {
      syntax_valid: true,
      module_format: 'ESM',
      has_component_export: false,
      exported_names: [],
      forbidden_dynamic_code: [],
      unexpected_node_apis: [],
      raw_fs_patterns: [],
      syntax_errors: [],
    },
    security: {
      is_secure: true,
      violations: [],
      env_accesses: [],
    },
    dependencies: {
      used_imports: [],
      undeclared_imports: [],
      forbidden_dependencies: [],
      unknown_external_dependencies: [],
    },
    typescript: {
      compiles: true,
      errors: [],
    },
  };

  // 1. In-memory fast AST analysis
  const fastProject = new Project({
    useInMemoryFileSystem: true,
    compilerOptions: { jsx: 1, strict: true, noEmit: true }
  });

  let sourceFile;
  try {
    sourceFile = fastProject.createSourceFile('candidate_virtual.tsx', source_code || '', { overwrite: true });
  } catch (err) {
    result.static_code.syntax_valid = false;
    result.static_code.syntax_errors.push(err.message);
    result.typescript.compiles = false;
    result.typescript.errors.push({ message: err.message, line: 1 });
    return result;
  }

  // Check for immediate parse/syntax errors
  const parseDiags = sourceFile.getPreEmitDiagnostics();
  const syntaxErrors = parseDiags.filter(d => {
    const code = d.getCode();
    // TS syntax error codes typically 1000..1999
    return code >= 1000 && code < 2000;
  });

  if (syntaxErrors.length > 0) {
    result.static_code.syntax_valid = false;
    for (const d of syntaxErrors) {
      result.static_code.syntax_errors.push({
        message: typeof d.getMessageText() === 'string' ? d.getMessageText() : d.getMessageText().getMessageText(),
        line: d.getLineNumber() || 1,
        code: d.getCode(),
      });
    }
  }

  // Check exports & module format
  const exportDeclarations = sourceFile.getExportedDeclarations();
  const exportedNames = Array.from(exportDeclarations.keys());
  result.static_code.exported_names = exportedNames;
  if (exportedNames.length > 0) {
    result.static_code.has_component_export = true;
  }

  // Check for CommonJS patterns
  const fullText = sourceFile.getFullText();
  if (/\bmodule\.exports\b/.test(fullText) || /\bexports\.\w+\s*=/.test(fullText)) {
    result.static_code.module_format = 'CommonJS';
  }

  // AST inspection for calls and identifiers
  const callExpressions = sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression);
  for (const call of callExpressions) {
    const exprText = call.getExpression().getText();
    const line = call.getStartLineNumber();

    if (FORBIDDEN_DYNAMIC_CALLS.has(exprText)) {
      result.static_code.forbidden_dynamic_code.push({
        kind: exprText,
        line,
        detail: call.getText().substring(0, 100),
      });
    }

    if (exprText === 'require') {
      const args = call.getArguments();
      if (args.length > 0) {
        const argText = args[0].getText().replace(/['"]/g, '');
        result.static_code.forbidden_dynamic_code.push({
          kind: 'dynamic_require',
          line,
          detail: `require('${argText}')`,
        });
        if (FORBIDDEN_SECURITY_MODULES.has(argText)) {
          result.security.violations.push({
            type: 'FORBIDDEN_IMPORT',
            module: argText,
            line,
            detail: `require('${argText}')`,
          });
        }
      }
    }

    if (call.getExpression().getKind() === SyntaxKind.ImportKeyword || exprText === 'import') {
      const args = call.getArguments();
      const argText = args.length > 0 ? args[0].getText().replace(/['"]/g, '') : '';
      result.static_code.forbidden_dynamic_code.push({
        kind: 'dynamic_import',
        line,
        detail: `import('${argText}')`,
      });
      if (FORBIDDEN_SECURITY_MODULES.has(argText)) {
        result.security.violations.push({
          type: 'FORBIDDEN_IMPORT',
          module: argText,
          line,
          detail: `import('${argText}')`,
        });
      }
    }

    if (exprText === 'setTimeout' || exprText === 'setInterval') {
      const args = call.getArguments();
      if (args.length > 0 && args[0].getKind() === SyntaxKind.StringLiteral) {
        result.static_code.forbidden_dynamic_code.push({
          kind: 'eval_timer_string',
          line,
          detail: `${exprText} with string evaluation`,
        });
      }
    }
  }

  // Check NewExpressions: new Function(...)
  const newExpressions = sourceFile.getDescendantsOfKind(SyntaxKind.NewExpression);
  for (const newExpr of newExpressions) {
    const exprText = newExpr.getExpression().getText();
    const line = newExpr.getStartLineNumber();
    if (exprText === 'Function') {
      result.static_code.forbidden_dynamic_code.push({
        kind: 'new_Function',
        line,
        detail: newExpr.getText().substring(0, 100),
      });
    }
  }

  // Check PropertyAccessExpressions: process.exit, process.env.*, etc.
  const propAccesses = sourceFile.getDescendantsOfKind(SyntaxKind.PropertyAccessExpression);
  for (const pa of propAccesses) {
    const text = pa.getText();
    const line = pa.getStartLineNumber();

    if (NODE_SPECIFIC_APIS.has(text)) {
      result.static_code.unexpected_node_apis.push({
        api: text,
        line,
      });
    }

    if (text.startsWith('process.env')) {
      const parts = text.split('.');
      const envKey = parts[2] || '';
      const isSensitive = SENSITIVE_ENV_KEYWORDS.some(k => envKey.toUpperCase().includes(k));
      result.security.env_accesses.push({
        env_key: envKey,
        is_sensitive: isSensitive,
        line,
        detail: text,
      });
      if (isSensitive) {
        result.security.violations.push({
          type: 'SENSITIVE_ENV_ACCESS',
          module: envKey,
          line,
          detail: text,
        });
      }
    }
  }

  // Check String Literals for raw filesystem paths
  const stringLiterals = sourceFile.getDescendantsOfKind(SyntaxKind.StringLiteral);
  for (const sl of stringLiterals) {
    const val = sl.getLiteralValue();
    if (RAW_FS_REGEX.test(val)) {
      result.static_code.raw_fs_patterns.push({
        pattern: val,
        line: sl.getStartLineNumber(),
      });
    }
  }

  // Check Imports
  const importDeclarations = sourceFile.getImportDeclarations();
  for (const imp of importDeclarations) {
    const mod = imp.getModuleSpecifierValue();
    const line = imp.getStartLineNumber();
    result.dependencies.used_imports.push(mod);

    // Check security forbidden modules
    if (FORBIDDEN_SECURITY_MODULES.has(mod)) {
      result.security.violations.push({
        type: 'FORBIDDEN_IMPORT',
        module: mod,
        line,
        detail: imp.getText(),
      });
    }
  }

  // Clean up fast in-memory project
  fastProject.removeSourceFile(sourceFile);

  // 2. TypeScript compilation with tsconfig if syntax is valid and not skipped
  if (!skip_tsc && result.static_code.syntax_valid) {
    try {
      const tsConfigPath = path.resolve(process.cwd(), 'tsconfig.json');
      const tsProject = new Project({
        tsConfigFilePath: tsConfigPath,
      });

      const candFile = tsProject.createSourceFile('__cand_temp_typecheck__.tsx', source_code || '', { overwrite: true });
      const fullDiags = candFile.getPreEmitDiagnostics();

      for (const d of fullDiags) {
        const msg = typeof d.getMessageText() === 'string' ? d.getMessageText() : d.getMessageText().getMessageText();
        result.typescript.errors.push({
          message: msg,
          line: d.getLineNumber() || 1,
          code: d.getCode(),
        });
      }

      if (result.typescript.errors.length > 0) {
        result.typescript.compiles = false;
      }

      tsProject.removeSourceFile(candFile);
    } catch (tscErr) {
      result.typescript.compiles = false;
      result.typescript.errors.push({
        message: `TypeScript diagnostic runner error: ${tscErr.message}`,
        line: 1,
        code: 9999,
      });
    }
  } else if (!result.static_code.syntax_valid) {
    result.typescript.compiles = false;
    result.typescript.errors = result.static_code.syntax_errors.map(e => ({
      message: typeof e === 'string' ? e : e.message,
      line: typeof e === 'object' ? e.line : 1,
      code: typeof e === 'object' ? e.code : 1000,
    }));
  }

  if (result.security.violations.length > 0) {
    result.security.is_secure = false;
  }

  return result;
}

// ─── CLI Entrypoint ──────────────────────────────────────────────────────────

function main() {
  let inputContent = '';
  if (process.argv.length > 2) {
    const inputPath = process.argv[2];
    inputContent = fs.readFileSync(inputPath, 'utf8');
  } else {
    inputContent = fs.readFileSync(0, 'utf8');
  }

  const inputJson = JSON.parse(inputContent);
  const result = analyze(inputJson);
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
}

if (require.main === module) {
  try {
    main();
  } catch (err) {
    process.stderr.write(`Worker Fatal Error: ${err.message}\n${err.stack}\n`);
    process.exit(1);
  }
}

module.exports = { analyze };
