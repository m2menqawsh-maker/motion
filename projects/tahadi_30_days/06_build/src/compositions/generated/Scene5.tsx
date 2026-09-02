import React from 'react';
import { AbsoluteFill, Sequence, spring, interpolate, interpolateColors, useCurrentFrame, useVideoConfig } from 'remotion';

export const Scene5: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Calculator pops up at 21.60s (frame 38 of this scene)
  const calcScale = spring({
    fps,
    frame: frame - 38,
    config: { damping: 12, mass: 1.2, stiffness: 100 }
  });

  // Calculate some buttons to light up (around frame 80)
  const buttonGlow = interpolateColors(
    spring({ fps, frame: frame - 80, config: { damping: 10 } }),
    [0, 1],
    ['rgba(255, 255, 255, 0.1)', '#00e5ff']
  );

  return (
    <AbsoluteFill>
      {/* Week 2 Badge */}
      <Sequence from={0} durationInFrames={143}>
        <AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'center', top: '150px' }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(20px)',
            border: '2px solid rgba(255, 0, 255, 0.5)',
            boxShadow: '0 0 30px rgba(255, 0, 255, 0.3)',
            padding: '30px 60px',
            borderRadius: '40px',
            transform: `scale(${spring({ fps, frame, config: { damping: 12 } })})`
          }}>
            <h1 style={{ 
              fontFamily: 'Alexandria', 
              fontSize: '80px', 
              color: '#fff', 
              margin: 0,
              fontWeight: '900'
            }}>
              الأسبوع 2
            </h1>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Calculator UI */}
      <Sequence from={38} durationInFrames={105}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', top: '50px' }}>
          
          <div style={{
            width: '400px',
            height: '600px',
            background: 'rgba(20, 20, 30, 0.8)',
            backdropFilter: 'blur(30px)',
            borderRadius: '40px',
            border: '2px solid rgba(255, 255, 255, 0.2)',
            boxShadow: '0 30px 60px rgba(0,0,0,0.8), 0 0 40px rgba(0, 229, 255, 0.2)',
            transform: `scale(${calcScale})`,
            display: 'flex',
            flexDirection: 'column',
            padding: '30px',
            boxSizing: 'border-box'
          }}>
            
            {/* Display Area */}
            <div style={{
              flex: '0 0 120px',
              background: 'rgba(0, 0, 0, 0.5)',
              borderRadius: '20px',
              marginBottom: '20px',
              display: 'flex',
              justifyContent: 'flex-end',
              alignItems: 'flex-end',
              padding: '20px',
              fontFamily: 'JetBrains Mono',
              fontSize: '50px',
              color: '#fff',
              border: '1px solid rgba(255, 255, 255, 0.1)'
            }}>
              30
            </div>

            {/* Buttons Grid */}
            <div style={{
              flex: '1',
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '15px'
            }}>
              {['AC', '±', '%', '÷', '7', '8', '9', '×', '4', '5', '6', '-', '1', '2', '3', '+', '0', '.', '='].map((btn, i) => {
                const isOp = ['÷', '×', '-', '+', '='].includes(btn);
                const isZero = btn === '0';
                const isEquals = btn === '=';
                
                return (
                  <div key={i} style={{
                    gridColumn: isZero ? 'span 2' : 'span 1',
                    background: isEquals ? buttonGlow : (isOp ? '#FF0055' : 'rgba(255, 255, 255, 0.1)'),
                    borderRadius: '20px',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    fontFamily: 'JetBrains Mono',
                    fontSize: '35px',
                    fontWeight: 'bold',
                    color: '#fff',
                    boxShadow: isEquals ? `0 0 20px ${buttonGlow}` : 'none'
                  }}>
                    {btn}
                  </div>
                );
              })}
            </div>

          </div>

        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
