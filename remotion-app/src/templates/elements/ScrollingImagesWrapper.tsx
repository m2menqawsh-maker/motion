import React from "react";
import { ScrollingColumns } from "remotion-bits";
import { Img } from "remotion";

export const ScrollingImagesWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const images = content?.images || surface?.images || [];
  const animProps = surface?.animation || {};

  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <div style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
      {images.length > 0 ? (
        <ScrollingColumns
 {...template_props}           direction={animProps.direction || "up"}
          speed={animProps.speed || 1}
          {...animProps}
        >
          {images.map((img: string, i: number) => (
             <Img key={i} src={img} style={{ width: surface?.imageWidth || 300, marginBottom: 20 }} />
          ))}
        </ScrollingColumns>
      ) : (
        <div style={{ color: "white", padding: 40 }}>Missing content.images</div>
      )}
    </div>
  </div>
  );
};
