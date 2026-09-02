import React from 'react';
import { AbsoluteFill, Sequence, spring, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export const Scene8: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // CTA Text pops in
  const textScale = spring({
    fps,
    frame: frame - 10,
    config: { damping: 12, mass: 1, stiffness: 100 }
  });

  // A "Subscribe" or "Start" button pops in
  const btnScale = spring({
    fps,
    frame: frame - 60,
    config: { damping: 14, mass: 1, stiffness: 120 }
  });

  // Simulated click at frame 120
  const clickScale = spring({
    fps,
    frame: frame - 120,
    config: { damping: 10, mass: 0.5, stiffness: 300 }
  });
  
  // Calculate final button scale
  const finalBtnScale = frame >= 120 
    ? interpolate(clickScale, [0, 1], [1, 0.9]) 
    : btnScale;

  const btnColor = frame >= 125 ? '#FF0055' : '#00e5ff';
  const textContent = frame >= 125 ? 'تم الانضمام ✔' : 'ابدأ التحدي الآن';

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={210}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
          
          <div style={{
            fontFamily: 'Alexandria',
            fontSize: '90px',
            fontWeight: '900',
            color: '#fff',
            textAlign: 'center',
            lineHeight: '1.4',
            transform: `scale(${textScale})`,
            direction: 'rtl',
            textShadow: '0 0 40px rgba(255,255,255,0.5)'
          }}>
            ابدأ تحدي <span style={{ color: '#00e5ff' }}>30 يوماً</span> اليوم
            <br />
            ولا تنظر للخلف!
          </div>

          <div style={{
            marginTop: '80px',
            background: btnColor,
            padding: '30px 80px',
            borderRadius: '50px',
            fontFamily: 'Alexandria',
            fontSize: '50px',
            fontWeight: 'bold',
            color: frame >= 125 ? '#fff' : '#000',
            boxShadow: `0 20px 50px ${btnColor}80`,
            transform: `scale(${finalBtnScale})`,
            transition: 'background 0.2s',
            direction: 'rtl'
          }}>
            {textContent}
          </div>

        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
