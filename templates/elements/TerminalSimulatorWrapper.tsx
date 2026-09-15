import React from "react";
import { TerminalSimulator } from "../../remotion-app/src/remotion/scenes/terminal-simulator";
import type { TemplateProps } from "../../../registry/types";

export const TerminalSimulatorWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const steps = content?.lines?.length > 1 
    ? content.lines.slice(1).map((line: string) => ({ text: line }))
    : undefined;

  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
      <TerminalSimulator  {...template_props} 
        title={surface?.text || "لوحة التحكم"} 
        command={content?.lines?.[0] || "بدء التشغيل..."}
        steps={steps}
        backgroundColor={surface?.background}
        accentColor={surface?.color}
      />
    </div>
  );
};
