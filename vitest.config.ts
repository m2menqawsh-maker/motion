import { defineConfig } from "vitest/config";
export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["tests/**/*.test.ts"]
  },
  resolve: {
    alias: {
      "@contracts": "/contracts",
      "@registry": "/registry",
      "@templates": "/templates",
      "@build": "/build/src",
    },
  },
});
