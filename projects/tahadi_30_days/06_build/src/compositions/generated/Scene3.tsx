import React from 'react';
import { AbsoluteFill, Sequence, spring, interpolate, interpolateColors, useCurrentFrame, useVideoConfig } from 'remotion';
import { TrackingIn } from '@templates/elements/typography/tracking-in/TrackingIn';

export const Scene3: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // "بل في الاستمرارية" starts at frame 91
  const mainTextPop = spring({
    fps,
    frame: frame - 91,
    config: { damping: 12, mass: 1, stiffness: 150 }
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000' }}>
      {/* 1. التمهيد */}
      <Sequence from={0} durationInFrames={91}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
          
          {/* Background glitching languages */}
          <div style={{ position: 'absolute', opacity: 0.1, fontSize: '150px', fontWeight: 'bold', fontFamily: 'monospace', color: '#fff' }}>
            <div style={{ position: 'absolute', top: '-300px', left: '-300px', opacity: (Math.floor(frame / 5) % 2) ? 1 : 0 }}>C++</div>
            <div style={{ position: 'absolute', top: '100px', right: '-350px', opacity: (Math.floor((frame+2) / 5) % 2) ? 1 : 0 }}>Java</div>
            <div style={{ position: 'absolute', bottom: '-400px', left: '100px', opacity: (Math.floor((frame+4) / 5) % 2) ? 1 : 0 }}>Python</div>
          </div>

          <div style={{ direction: 'rtl' }}>
            <TrackingIn
              text="السر ليس في اللغة التي تختارها"
              delay={0}
              duration={30}
              color="#ffffff"
              fontSize={85}
              tracking={0}
              fromTracking={0.2}
            />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* 2. الرسالة الأساسية - شبكة الـ 30 يوم */}
      <Sequence from={91} durationInFrames={64}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', top: '-150px' }}>
          
          <div style={{
            fontFamily: 'Alexandria',
            fontSize: '90px',
            fontWeight: '900',
            color: '#00e5ff',
            textShadow: '0 0 30px rgba(0, 229, 255, 0.8)',
            transform: `scale(${mainTextPop})`,
            direction: 'rtl'
          }}>
            بل في الاستمرارية
          </div>
          
          {/* Calendar Grid */}
          <div style={{
            marginTop: '80px',
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: '15px',
            transform: `scale(${spring({ fps, frame: frame - 91, config: { damping: 15 } })})`
          }}>
            {Array.from({ length: 30 }).map((_, i) => {
              // Each square lights up sequentially
              const squareFillProgress = interpolate(
                frame - 91 - (i * 1.5), 
                [0, 5], 
                [0, 1], 
                { extrapolateRight: 'clamp', extrapolateLeft: 'clamp' }
              );
              
              const bgColor = interpolateColors(
                squareFillProgress,
                [0, 1],
                ['rgba(255,255,255,0.05)', '#00e5ff']
              );
              
              const boxShadow = interpolateColors(
                squareFillProgress,
                [0, 1],
                ['0 0 0px rgba(0,229,255,0)', '0 0 20px rgba(0,229,255,0.8)']
              );

              return (
                <div key={i} style={{
                  width: '60px',
                  height: '60px',
                  borderRadius: '12px',
                  backgroundColor: bgColor,
                  boxShadow: boxShadow,
                  border: '2px solid rgba(255,255,255,0.1)'
                }} />
              );
            })}
          </div>

        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
