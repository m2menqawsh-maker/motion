import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["tests/**/*.test.ts"]
  },
  resolve: {
    dedupe: ["remotion", "@remotion/transitions", "@remotion/cli", "react", "react-dom"],
    alias: {
      "@": path.resolve(import.meta.dirname, "remotion-app/src"),
      "@contracts": path.resolve(import.meta.dirname, "contracts"),
      "@registry": path.resolve(import.meta.dirname, "registry"),
      "@templates": path.resolve(import.meta.dirname, "templates"),
      "@build": path.resolve(import.meta.dirname, "build/src"),
      "remotion": path.resolve(import.meta.dirname, "node_modules/remotion"),
    },
  },
});
