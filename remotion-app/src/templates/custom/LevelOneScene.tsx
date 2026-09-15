import React from "react";
import { z } from "zod";
import { CodeBlockWrapper } from "../elements/CodeBlockWrapper";
import { LevelZeroBox } from "./LevelZeroBox";

export const schema = z.object({
  layout: z.enum(["split", "stack"]).optional()
});

export const LevelOneScene = ({ surface, content, template_props }: any) => {
  const isSplit = template_props?.layout === "split";

  return (
    <div style={{
      width: "100%", height: "100%",
      display: "flex", 
      flexDirection: isSplit ? "row" : "column",
      backgroundColor: surface?.background || "#111"
    }}>
      <div style={{ flex: 1, padding: 20 }}>
         {/* Using Level 0 Lego Block */}
         <LevelZeroBox 
            surface={{...surface, text: surface?.title || "My Combined Scene"}} 
            content={{text: "Powered by Level 0 Block"}} 
            template_props={{glowColor: "#f0f", borderWidth: 2}} 
         />
      </div>
      <div style={{ flex: 1, padding: 20 }}>
         {/* Using pre-existing Lego Block */}
         <CodeBlockWrapper 
            surface={surface} 
            content={content} 
            template_props={{...template_props}} 
         />
      </div>
    </div>
  );
};
