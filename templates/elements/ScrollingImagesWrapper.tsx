import React from "react";
import { ScrollingImages } from "remotion-bits";
import { Img } from "remotion";

export const ScrollingImagesWrapper = ({ surface, content }: any) => {
  const images = content?.images || surface?.images || [];
  const animProps = surface?.animation || {};

  return (
    <div style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }}>
      {images.length > 0 ? (
        <ScrollingImages
          direction={animProps.direction || "up"}
          speed={animProps.speed || 1}
          {...animProps}
        >
          {images.map((img: string, i: number) => (
             <Img key={i} src={img} style={{ width: surface?.imageWidth || 300, marginBottom: 20 }} />
          ))}
        </ScrollingImages>
      ) : (
        <div style={{ color: "white", padding: 40 }}>Missing content.images</div>
      )}
    </div>
  );
};
