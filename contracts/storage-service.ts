/**
 * contracts/storage-service.ts — Engine-Neutral StorageService Contract & Validation.
 * S28-R14: Enforces the production storage boundary in TypeScript.
 * 
 * Invariants:
 * - Persistent renderer/editor outputs must go through StorageService.
 * - Server-generated canonical storage keys:
 *   workspaces/{workspace_id}/projects/{project_id}/{category}/{item_id}/{filename}
 * - Fail-closed path traversal validation: rejects absolute paths, "..", illegal characters.
 * - Worker disk is temporary execution space only.
 */

import * as fs from "fs";
import * as path from "path";

export interface StorageMetadata {
  key: string;
  sizeBytes: number;
  contentType: string;
  sha256?: string;
  lastModified?: string;
}

export class StorageSecurityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "StorageSecurityError";
  }
}

const SAFE_KEY_PATTERN = /^[a-zA-Z0-9_\-\.\/]+$/;

export function validateStorageKey(key: string): string {
  if (!key || typeof key !== "string") {
    throw new StorageSecurityError("Storage key must be a non-empty string.");
  }

  if (key.startsWith("/")) {
    throw new StorageSecurityError(`Storage key cannot start with a slash (absolute path forbidden): '${key}'`);
  }

  const normalized = key.trim();
  if (!normalized) {
    throw new StorageSecurityError("Storage key cannot be empty or root.");
  }

  const parts = normalized.split("/");
  for (const p of parts) {
    if (p === "" || p === "." || p === "..") {
      throw new StorageSecurityError(`Invalid path segment in storage key '${key}': '${p}'`);
    }
  }

  if (!SAFE_KEY_PATTERN.test(normalized)) {
    throw new StorageSecurityError(`Storage key contains illegal characters: '${key}'`);
  }

  return normalized;
}

export function buildStorageKey(
  workspaceId: string,
  projectId: string,
  category: string,
  itemId: string,
  filename: string
): string {
  const args = [
    { val: workspaceId, name: "workspaceId" },
    { val: projectId, name: "projectId" },
    { val: category, name: "category" },
    { val: itemId, name: "itemId" },
    { val: filename, name: "filename" },
  ];

  for (const { val, name } of args) {
    if (!val || val.includes("..") || val.includes("/") || val.includes("\\")) {
      throw new StorageSecurityError(`Invalid ${name} for storage key: '${val}'`);
    }
  }

  const rawKey = `workspaces/${workspaceId}/projects/${projectId}/${category}/${itemId}/${filename}`;
  return validateStorageKey(rawKey);
}

export interface IStorageService {
  put(key: string, data: Buffer | Uint8Array | string, contentType?: string): Promise<StorageMetadata>;
  get(key: string): Promise<Buffer>;
  exists(key: string): Promise<boolean>;
  delete(key: string): Promise<boolean>;
  metadata(key: string): Promise<StorageMetadata>;
}

export class LocalStorageService implements IStorageService {
  private readonly baseDir: string;

  constructor(baseDir: string = "data/storage") {
    this.baseDir = path.resolve(baseDir);
    fs.mkdirSync(this.baseDir, { recursive: true });
  }

  private resolvePath(key: string): string {
    const validKey = validateStorageKey(key);
    const resolved = path.resolve(this.baseDir, validKey);
    if (!resolved.startsWith(this.baseDir)) {
      throw new StorageSecurityError(`Path traversal attempt detected: '${key}'`);
    }
    return resolved;
  }

  async put(key: string, data: Buffer | Uint8Array | string, contentType = "application/octet-stream"): Promise<StorageMetadata> {
    const filePath = this.resolvePath(key);
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    const buffer = Buffer.isBuffer(data) ? data : Buffer.from(data);
    fs.writeFileSync(filePath, buffer);

    return {
      key,
      sizeBytes: buffer.byteLength,
      contentType,
      lastModified: new Date().toISOString(),
    };
  }

  async get(key: string): Promise<Buffer> {
    const filePath = this.resolvePath(key);
    if (!fs.existsSync(filePath)) {
      throw new Error(`Storage object not found: '${key}'`);
    }
    return fs.readFileSync(filePath);
  }

  async exists(key: string): Promise<boolean> {
    const filePath = this.resolvePath(key);
    return fs.existsSync(filePath);
  }

  async delete(key: string): Promise<boolean> {
    const filePath = this.resolvePath(key);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
      return true;
    }
    return false;
  }

  async metadata(key: string): Promise<StorageMetadata> {
    const filePath = this.resolvePath(key);
    if (!fs.existsSync(filePath)) {
      throw new Error(`Storage object not found: '${key}'`);
    }
    const stat = fs.statSync(filePath);
    return {
      key,
      sizeBytes: stat.size,
      contentType: "application/octet-stream",
      lastModified: stat.mtime.toISOString(),
    };
  }
}
