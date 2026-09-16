import React from 'react';

const DummyEffect: React.FC<any> = ({ children }) => <>{children}</>;

export const EFFECT_COMPONENTS: Record<string, React.ComponentType<any>> = {
  "AudioManager": DummyEffect,
  "CameraRig": DummyEffect,
  "CountUp": DummyEffect,
  "Enter": DummyEffect,
  "Exit": DummyEffect,
  "Highlight": DummyEffect,
  "Pulse": DummyEffect,
  "Stagger": DummyEffect,
  "TrafficLights": DummyEffect,
  "Wallpaper": DummyEffect,
  "camera-shake": DummyEffect,
};

export const EngineBridge: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <div style={{width: '100%', height: '100%'}}>{children}</div>;
};
