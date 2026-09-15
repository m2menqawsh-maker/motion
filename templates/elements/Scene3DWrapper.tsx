import React from "react";
import { DeviceMockupZoom } from "../../remotion-app/src/remotion/scenes/device-mockup-zoom";
import type { TemplateProps } from "../../../registry/types";

export const Scene3DWrapper: React.FC<TemplateProps> = ({ surface }) => {
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <DeviceMockupZoom  {...template_props} 
      device="phone"
      title={surface?.text || undefined} 
      subtitle={surface?.subtext || undefined} 
      backgroundColor={surface?.background || "#0B0C11"}
      accentColor={surface?.color}
    />
  </div>
  );
};
