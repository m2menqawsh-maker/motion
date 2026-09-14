import React from "react";
import { ChatToPreview } from "../../remotion-app/src/remotion/scenes/chat-to-preview";
import type { TemplateProps } from "../../../registry/types";

export const ChatToPreviewWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <ChatToPreview messages={content?.items ? content.items.map(i => ({role: "user", text: i})) : undefined} />
  );
};
