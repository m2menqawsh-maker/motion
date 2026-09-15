import React from "react";
import { HeroDeviceAssemble } from "../../remotion-app/src/compositions/hero-device-assemble";
import type { TemplateProps } from "../../../registry/types";

export const HeroDeviceAssembleWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <HeroDeviceAssemble  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
