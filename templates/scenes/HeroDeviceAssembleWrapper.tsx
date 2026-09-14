import React from "react";
import { HeroDeviceAssemble } from "../../remotion-app/src/compositions/hero-device-assemble";
import type { TemplateProps } from "../../../registry/types";

export const HeroDeviceAssembleWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <HeroDeviceAssemble title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
