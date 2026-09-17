import { describe, it, expect } from "vitest";
import React from "react";
import {
  DataStory,
  DataStoryPropsSchema,
  DEFAULT_BAR_DATA,
  DEFAULT_METRICS,
  DEFAULT_STEPS,
} from "../remotion-app/src/compositions/data-story";
import { ZodError } from "zod";

describe("DataStory Prop Contract & Runtime Behavior", () => {
  describe("1. Canonical Historical Defaults on Omission", () => {
    it("has exact historical defaults from commit 9dcb888b", () => {
      expect(DEFAULT_BAR_DATA).toEqual([
        { label: "Q1", value: 40 },
        { label: "Q2", value: 65 },
        { label: "Q3", value: 85 },
        { label: "Q4", value: 95 },
      ]);
      expect(DEFAULT_METRICS).toEqual([
        { label: "Throughput", value: 120, suffix: "%" },
        { label: "Latency", value: 636, suffix: "ms" },
        { label: "Templates", value: 172 },
      ]);
      expect(DEFAULT_STEPS).toEqual([
        { title: "Discovery", description: "Scan templates and indexes" },
        { title: "Composition", description: "Assemble dynamic timeline" },
        { title: "Studio", description: "Live instant preview" },
      ]);
    });

    it("accepts empty object and parses successfully", () => {
      const parsed = DataStoryPropsSchema.parse({});
      expect(parsed.barData).toBeUndefined();
      expect(parsed.metrics).toBeUndefined();
      expect(parsed.steps).toBeUndefined();
    });

    it("renders DataStory without throwing when props are omitted", () => {
      expect(() => {
        // Render element creation
        React.createElement(DataStory, {});
      }).not.toThrow();
    });
  });

  describe("2. Explicit Empty Array Preservation (Omitted != Empty)", () => {
    it("parses explicit empty arrays without error", () => {
      const parsed = DataStoryPropsSchema.parse({
        barData: [],
        metrics: [],
        steps: [],
      });
      expect(parsed.barData).toEqual([]);
      expect(parsed.metrics).toEqual([]);
      expect(parsed.steps).toEqual([]);
    });

    it("preserves explicit [] in component execution", () => {
      const element = DataStory({
        barData: [],
        metrics: [],
        steps: [],
      });
      expect(element).toBeDefined();
    });
  });

  describe("3. Custom Valid Data Propagation", () => {
    it("passes customized data through successfully", () => {
      const customBars = [{ label: "Custom", value: 99, delta: "+10%" }];
      const customMetrics = [{ label: "Speed", value: 50, suffix: "fps" }];
      const customSteps = [{ title: "Step 1", description: "Do thing" }];

      const parsed = DataStoryPropsSchema.parse({
        barData: customBars,
        metrics: customMetrics,
        steps: customSteps,
      });

      expect(parsed.barData).toEqual(customBars);
      expect(parsed.metrics).toEqual(customMetrics);
      expect(parsed.steps).toEqual(customSteps);

      const element = DataStory({
        barData: customBars,
        metrics: customMetrics,
        steps: customSteps,
      });
      expect(element).toBeDefined();
    });
  });

  describe("4. Fail-Closed Malformed Input Rejection", () => {
    it("rejects malformed barData (string, null, object, bad items)", () => {
      expect(() => DataStoryPropsSchema.parse({ barData: "string" })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ barData: null })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ barData: {} })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ barData: [{ label: 123, value: 40 }] })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ barData: [{ label: "Q1", value: "not_a_number" }] })).toThrow();
      expect(() => DataStory({ barData: "invalid" as any })).toThrow();
    });

    it("rejects malformed metrics (string, null, object, bad items)", () => {
      expect(() => DataStoryPropsSchema.parse({ metrics: "string" })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ metrics: null })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ metrics: {} })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ metrics: [{ label: "M1", value: "not_a_number" }] })).toThrow();
      expect(() => DataStory({ metrics: "invalid" as any })).toThrow();
    });

    it("rejects malformed steps (string, null, object, bad items)", () => {
      expect(() => DataStoryPropsSchema.parse({ steps: "string" })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ steps: null })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ steps: {} })).toThrow();
      expect(() => DataStoryPropsSchema.parse({ steps: [{ title: 123 }] })).toThrow();
      expect(() => DataStory({ steps: "invalid" as any })).toThrow();
    });
  });
});
