import React from 'react';
import type { StyleSurface } from '../contracts/StyleSurface';
import type { SceneContent } from '../contracts/SceneContent';
import { EFFECT_COMPONENTS } from './effects/engine-bridge';

export const Timeline: React.FC<{
  surface: StyleSurface;
  content?: SceneContent;
}> = ({ surface, content }) => {
  const points = content?.lines && content.lines.length > 0
    ? content.lines
    : ['Concept', 'Build', 'Ship', 'Iterate'];

  const isRTL = surface.fontFamily === 'Cairo' || surface.fontFamily === 'Tajawal';
  const direction = isRTL ? 'rtl' : 'ltr';

  const lineColor = surface.emphasis || '#26262E';
  const dotColor = surface.color || '#F2F2F4';
  const accentColor = surface.background || '#D96B82'; 
  const labelColor = surface.subtext || '#8E8E98';

  const Stagger = EFFECT_COMPONENTS["Stagger"];
  const Enter = EFFECT_COMPONENTS["Enter"];

  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex',
      flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
      fontFamily: surface.fontFamily, color: labelColor,
      opacity: surface.opacity, direction,
      ...(surface.position as any)
    }}>
      <div style={{
        display: 'flex', flexDirection: 'row', alignItems: 'center',
        justifyContent: 'space-between', width: '80%', maxWidth: 1200, position: 'relative',
        ...(surface.styleOverride as React.CSSProperties)
      }}>
        {/* Animated Line using engine primitive */}
        {Enter ? (
          <Enter delay={0} duration={30} scaleFrom={0} translateY={0} translateX={0}>
             <div style={{
                position: 'absolute', top: 7, left: 0, right: 0, height: 2,
                backgroundColor: lineColor, transformOrigin: isRTL ? 'right center' : 'left center',
             }} />
          </Enter>
        ) : (
          <div style={{
            position: 'absolute', top: 7, left: 0, right: 0, height: 2,
            backgroundColor: lineColor, transformOrigin: isRTL ? 'right center' : 'left center',
          }} />
        )}
        
        {/* Anchor Points using engine Stagger primitive */}
        {Stagger ? (
           <Stagger interval={10} delay={15} duration={15} translateY={20} scaleFrom={0} style={{ display: 'flex', width: '100%', justifyContent: 'space-between' }}>
             {points.map((label, i) => {
               const isLast = i === points.length - 1;
               const currentDotColor = isLast ? accentColor : dotColor;
               return (
                 <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
                   <div style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: currentDotColor, marginBottom: 8, zIndex: 1 }} />
                   <span style={{ fontSize: surface.fontSize || '22px', fontWeight: surface.fontWeight || 500, whiteSpace: 'nowrap' }}>{label}</span>
                 </div>
               );
             })}
           </Stagger>
        ) : (
           <div style={{ display: 'flex', width: '100%', justifyContent: 'space-between' }}>
             {points.map((label, i) => {
                 const isLast = i === points.length - 1;
                 const currentDotColor = isLast ? accentColor : dotColor;
                 return (
                   <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
                     <div style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: currentDotColor, marginBottom: 8, zIndex: 1 }} />
                     <span style={{ fontSize: surface.fontSize || '22px', fontWeight: surface.fontWeight || 500, whiteSpace: 'nowrap' }}>{label}</span>
                   </div>
                 );
             })}
           </div>
        )}
      </div>
    </div>
  );
};
