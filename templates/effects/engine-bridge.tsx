import React from 'react';

// --- Imports ---
import { AudioManager } from "../../engine/audio/AudioManager";
import { CameraRig } from "../../engine/camera/CameraRig";
import { CountUp } from "../../engine/primitives/CountUp";
import { Enter } from "../../engine/primitives/Enter";
import { Exit } from "../../engine/primitives/Exit";
import { Highlight } from "../../engine/primitives/Highlight";
import { Pulse } from "../../engine/primitives/Pulse";
import { Stagger } from "../../engine/primitives/Stagger";
import { TrafficLights } from "../../engine/primitives/TrafficLights";
import { Wallpaper } from "../../engine/primitives/Wallpaper";

export const EFFECT_COMPONENTS: Record<string, React.ComponentType<any>> = {
  "AudioManager": AudioManager,
  "CameraRig": CameraRig,
  "CountUp": CountUp,
  "Enter": Enter,
  "Exit": Exit,
  "Highlight": Highlight,
  "Pulse": Pulse,
  "Stagger": Stagger,
  "TrafficLights": TrafficLights,
  "Wallpaper": Wallpaper,
  "camera-shake": CameraRig,
};

export const EngineBridge: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <div style={{width: '100%', height: '100%'}}>{children}</div>;
};

