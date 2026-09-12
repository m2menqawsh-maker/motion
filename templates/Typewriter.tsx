import React from 'react';
import type { StyleSurface } from '../contracts/StyleSurface';
import type { SceneContent } from '../contracts/SceneContent';

export const Typewriter: React.FC<{
  surface: StyleSurface;
  content?: SceneContent;
}> = ({ surface, content }) => {
  const progress = (surface as any).animation?.progress ?? 1;
  const opacity = (surface as any).animation?.opacity ?? 1;
  
  const isRTL = surface.fontFamily === 'Cairo' || surface.fontFamily === 'Tajawal';
  const direction = isRTL ? 'rtl' : 'ltr';

  const text = surface.text || 'Typewriter';
  const subtext = surface.subtext || '';

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      fontFamily: surface.fontFamily,
      color: surface.color || '#F2F2F4',
      opacity: surface.opacity !== undefined ? surface.opacity : opacity,
      direction,
      ...(surface.position as any),
      ...(surface.styleOverride as React.CSSProperties)
    }}>
      <div style={{
        transform: `scale(${progress})`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 16
      }}>
        <div style={{ fontSize: surface.fontSize || 48, fontWeight: surface.fontWeight || 600 }}>
          {text}
        </div>
        {subtext && (
          <div style={{ fontSize: (surface.fontSize || 48) * 0.5, color: surface.subtext || '#8E8E98' }}>
            {subtext}
          </div>
        )}
      </div>
    </div>
  );
};
