import React from "react";
import { CodeBlock } from "remotion-bits";

export const CodeBlockWrapper = ({ surface, content }: any) => {
  const code = content?.text || content?.lines?.join("\n") || "console.log('Hello World');";
  const animProps = surface?.animation || {};
  
  return (
    <div style={{ width: "100%", height: "100%", padding: 40, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <CodeBlock
        code={code}
        language={surface?.language || "typescript"}
        {...animProps}
        style={{
          fontSize: surface?.fontSize || 40,
          borderRadius: 20,
          width: "100%"
        }}
      />
    </div>
  );
};
