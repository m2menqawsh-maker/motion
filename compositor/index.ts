/**
 * compositor/index.ts — Master Compositor & Output Normalization Subsystem.
 * S28-R11: Decouples final video assembly and multi-engine normalization from specific rendering engines.
 */

export * from "./probe";
export * from "./output-normalizer";
export * from "./audio-normalizer";
export * from "./timeline-assembler";
export * from "./master-compositor";
export * from "./qc-adapter";
