import React from "react";
import { DeviceMockupZoom } from "@/remotion/scenes/device-mockup-zoom";
import { staticFile } from "remotion";
import type { TemplateProps } from "@registry/types";

export const DeviceMockupZoomWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const imgSrc = content?.icons?.[0] ? staticFile(content.icons[0]) : undefined;
  
  const customScreen = content?.lines && content.lines.length > 0 ? (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', backgroundColor: '#0B0C11', color: 'white', fontFamily: surface?.fontFamily || 'sans-serif' }}>
       {imgSrc && <img src={imgSrc} style={{ width: 160, height: 160, marginBottom: 30 }} alt="" />}
       {content.lines.map((line: string, i: number) => (
          <div key={i} style={{ fontSize: i === 0 ? 32 : 24, fontWeight: 'bold', color: i === 0 ? (surface?.color || 'white') : '#9ca3af', textAlign: 'center', marginTop: i > 0 ? 15 : 0, direction: 'rtl' }}>{line}</div>
       ))}
    </div>
  ) : undefined;

  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <DeviceMockupZoom  {...template_props} 
      title={surface?.text || undefined} 
      subtitle={surface?.subtext || undefined} 
      src={customScreen ? undefined : imgSrc}
      backgroundColor={surface?.background}
      accentColor={surface?.color}
    >
      {customScreen}
    </DeviceMockupZoom>
  </div>
  );
};
