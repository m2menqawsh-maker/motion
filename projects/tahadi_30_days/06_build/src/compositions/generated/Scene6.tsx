import React from 'react';
import { AbsoluteFill, Sequence, spring, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export const Scene6: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Code window pops up at start
  const windowScale = spring({
    fps,
    frame: frame - 10,
    config: { damping: 14, mass: 1, stiffness: 120 }
  });

  // Glitch/Fade effect for "from memory" starting around frame 120 (34s - 30.02s = ~4s = 120f)
  const memoryFade = interpolate(
    frame,
    [120, 160],
    [1, 0.1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const glitchBlur = interpolate(
    frame,
    [120, 140, 160],
    [0, 10, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  return (
    <AbsoluteFill>
      {/* Week 4 Badge */}
      <Sequence from={0} durationInFrames={240}>
        <AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'center', top: '150px' }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(20px)',
            border: '2px solid rgba(255, 165, 0, 0.5)',
            boxShadow: '0 0 30px rgba(255, 165, 0, 0.3)',
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
              الأسبوع 4
            </h1>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Code Editor Window */}
      <Sequence from={10} durationInFrames={230}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', top: '80px' }}>
          <div style={{
            width: '800px',
            background: '#1e1e1e',
            borderRadius: '20px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.8), 0 0 20px rgba(255, 165, 0, 0.2)',
            overflow: 'hidden',
            transform: `scale(${windowScale})`,
            border: '1px solid #333'
          }}>
            {/* Window Header */}
            <div style={{
              height: '40px',
              background: '#2d2d2d',
              display: 'flex',
              alignItems: 'center',
              padding: '0 20px',
              gap: '10px'
            }}>
              <div style={{ width: '15px', height: '15px', borderRadius: '50%', background: '#ff5f56' }} />
              <div style={{ width: '15px', height: '15px', borderRadius: '50%', background: '#ffbd2e' }} />
              <div style={{ width: '15px', height: '15px', borderRadius: '50%', background: '#27c93f' }} />
            </div>

            {/* Code Content */}
            <div style={{
              padding: '40px',
              fontFamily: 'JetBrains Mono',
              fontSize: '32px',
              lineHeight: '1.6',
              color: '#d4d4d4',
              opacity: memoryFade,
              filter: `blur(${glitchBlur}px)`,
              textAlign: 'left'
            }}>
              <span style={{ color: '#569cd6' }}>function</span> <span style={{ color: '#dcdcaa' }}>calculateSum</span>(a, b) {'{'}<br/>
              &nbsp;&nbsp;<span style={{ color: '#c586c0' }}>if</span> (a &lt; <span style={{ color: '#b5cea8' }}>0</span> || b &lt; <span style={{ color: '#b5cea8' }}>0</span>) {'{'}<br/>
              &nbsp;&nbsp;&nbsp;&nbsp;<span style={{ color: '#c586c0' }}>return</span> <span style={{ color: '#ce9178' }}>"Error"</span>;<br/>
              &nbsp;&nbsp;{'}'}<br/>
              &nbsp;&nbsp;<span style={{ color: '#c586c0' }}>return</span> a + b;<br/>
              {'}'}<br/><br/>
              <span style={{ color: '#569cd6' }}>const</span> result = <span style={{ color: '#dcdcaa' }}>calculateSum</span>(<span style={{ color: '#b5cea8' }}>10</span>, <span style={{ color: '#b5cea8' }}>20</span>);<br/>
              console.<span style={{ color: '#dcdcaa' }}>log</span>(result);
            </div>
          </div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
