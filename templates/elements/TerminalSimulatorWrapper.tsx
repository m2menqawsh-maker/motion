import React from "react";
import { TerminalSimulator } from "../../remotion-app/src/remotion/scenes/terminal-simulator";
import type { TemplateProps } from "../../../registry/types";

export const TerminalSimulatorWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <TerminalSimulator title={content?.text || undefined} />
  );
};
