import React from "react";
import { TabSwitchPanel } from "../../remotion-app/src/remotion/scenes/tab-switch-panel";
import type { TemplateProps } from "../../../registry/types";

export const TabSwitchPanelWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <TabSwitchPanel  {...template_props}  />
  </div>
  );
};
