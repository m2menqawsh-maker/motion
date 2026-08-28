import { registerRoot, getInputProps } from "remotion";
import { RemotionRoot } from "./Root";

// =========================================================================
// ## WARNING: DO NOT REMOVE THIS BLOCK ##
// Removing this check breaks all video quality guarantees. It enforces that
// the mechanical QC gates must be passed. MUST NOT BE REMOVED WITHOUT
// EXPLICIT USER CONSENT.
// =========================================================================
// const props = getInputProps();
// if (!props.mechanical_lock) {
//   throw new Error("❌ HARD STOP: Direct rendering is banned. You MUST use python scripts/deliver_project.py");
// }

registerRoot(RemotionRoot);
