import React from 'react';
import { AbsoluteFill, Sequence, spring, interpolate, useCurrentFrame, useVideoConfig, Img, staticFile } from 'remotion';
import { TrackingIn } from '@templates/elements/typography/tracking-in/TrackingIn';

export const Scene4: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // "اختر لغة واحدة مثلا بايثون" starts at 14.14s (frame 33 of this scene)
  const pythonScale = spring({
    fps,
    frame: frame - 33,
    config: { damping: 10, mass: 1, stiffness: 120 }
  });

  const pythonRotation = interpolate(
    frame,
    [33, 201],
    [0, 360],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  // Chips start at 16.96s (frame 118 of this scene)
  const chip1Scale = spring({ fps, frame: frame - 118, config: { damping: 12 } });
  const chip2Scale = spring({ fps, frame: frame - 128, config: { damping: 12 } });
  const chip3Scale = spring({ fps, frame: frame - 138, config: { damping: 12 } });
  const chip4Scale = spring({ fps, frame: frame - 148, config: { damping: 12 } });
  const chip5Scale = spring({ fps, frame: frame - 158, config: { damping: 12 } });
  const chip6Scale = spring({ fps, frame: frame - 168, config: { damping: 12 } });

  // Floating effect for chips
  const float1 = Math.sin(frame / 15) * 15;
  const float2 = Math.cos(frame / 15) * 15;
  const float3 = Math.sin((frame + 30) / 15) * 15;
  const float4 = Math.cos((frame + 20) / 15) * 15;
  const float5 = Math.sin((frame + 50) / 15) * 15;
  const float6 = Math.cos((frame + 80) / 15) * 15;

  return (
    <AbsoluteFill>
      {/* Week 1 Badge */}
      <Sequence from={0} durationInFrames={201}>
        <AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'center', top: '150px' }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(20px)',
            border: '2px solid rgba(0, 229, 255, 0.5)',
            boxShadow: '0 0 30px rgba(0, 229, 255, 0.3)',
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
              الأسبوع 1
            </h1>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Python Icon & Glow */}
      <Sequence from={33} durationInFrames={168}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', top: '50px' }}>
          {/* Outer Glow */}
          <div style={{
            position: 'absolute',
            width: '400px',
            height: '400px',
            background: 'radial-gradient(circle, rgba(0,229,255,0.4) 0%, rgba(0,0,0,0) 70%)',
            transform: `scale(${pythonScale})`,
            opacity: 0.8
          }} />
          
          <Img 
            src={staticFile('media/icon_python.svg')} 
            style={{ 
              width: '350px', 
              height: '350px',
              transform: `scale(${pythonScale}) rotate(${pythonRotation}deg)` 
            }} 
          />
        </AbsoluteFill>
      </Sequence>

      {/* The 6 Chips (Basics) */}
      <Sequence from={118} durationInFrames={83}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', top: '50px' }}>
          
          {/* Chip 1: Variables (Top Left) */}
          <div style={{
            position: 'absolute',
            top: '550px',
            left: '120px',
            background: 'linear-gradient(45deg, #FF0055, #FF00AA)',
            padding: '15px 30px',
            borderRadius: '40px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '35px',
            fontWeight: 'bold',
            color: '#fff',
            boxShadow: '0 10px 30px rgba(255,0,85,0.5)',
            transform: `scale(${chip1Scale}) translateY(${float1}px) rotate(-10deg)`
          }}>
            x = 10
          </div>

          {/* Chip 2: If/Else (Top Right) */}
          <div style={{
            position: 'absolute',
            top: '600px',
            right: '120px',
            background: 'linear-gradient(45deg, #00FFAA, #0055FF)',
            padding: '15px 30px',
            borderRadius: '40px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '35px',
            fontWeight: 'bold',
            color: '#fff',
            boxShadow: '0 10px 30px rgba(0,255,170,0.5)',
            transform: `scale(${chip2Scale}) translateY(${float2}px) rotate(15deg)`
          }}>
            if x &gt; 5:
          </div>

          {/* Chip 5: Lists (Mid Left) */}
          <div style={{
            position: 'absolute',
            top: '900px',
            left: '80px',
            background: 'linear-gradient(45deg, #FF4500, #DC143C)',
            padding: '15px 30px',
            borderRadius: '40px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '35px',
            fontWeight: 'bold',
            color: '#fff',
            boxShadow: '0 10px 30px rgba(255,69,0,0.5)',
            transform: `scale(${chip5Scale}) translateY(${float5}px) rotate(-12deg)`
          }}>
            [1, 2, 3]
          </div>

          {/* Chip 4: Print (Mid Right) */}
          <div style={{
            position: 'absolute',
            top: '950px',
            right: '80px',
            background: 'linear-gradient(45deg, #8A2BE2, #4B0082)',
            padding: '15px 30px',
            borderRadius: '40px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '35px',
            fontWeight: 'bold',
            color: '#fff',
            boxShadow: '0 10px 30px rgba(138,43,226,0.5)',
            transform: `scale(${chip4Scale}) translateY(${float4}px) rotate(8deg)`
          }}>
            print("Hello")
          </div>

          {/* Chip 3: Loops (Bottom Left) */}
          <div style={{
            position: 'absolute',
            top: '1250px',
            left: '150px',
            background: 'linear-gradient(45deg, #FFD700, #FF8C00)',
            padding: '15px 30px',
            borderRadius: '40px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '35px',
            fontWeight: 'bold',
            color: '#fff',
            boxShadow: '0 10px 30px rgba(255,215,0,0.5)',
            transform: `scale(${chip3Scale}) translateY(${float3}px) rotate(-5deg)`
          }}>
            for i in range(5):
          </div>

          {/* Chip 6: Functions (Bottom Right) */}
          <div style={{
            position: 'absolute',
            top: '1300px',
            right: '150px',
            background: 'linear-gradient(45deg, #2E8B57, #3CB371)',
            padding: '15px 30px',
            borderRadius: '40px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '35px',
            fontWeight: 'bold',
            color: '#fff',
            boxShadow: '0 10px 30px rgba(46,139,87,0.5)',
            transform: `scale(${chip6Scale}) translateY(${float6}px) rotate(5deg)`
          }}>
            def func():
          </div>

        </AbsoluteFill>
      </Sequence>

    </AbsoluteFill>
  );
};
