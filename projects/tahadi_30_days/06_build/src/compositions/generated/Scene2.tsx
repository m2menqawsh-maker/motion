// GENERATED — DO NOT EDIT
// Hash: 1416976fca6067be6ed2ea9fae40334f
import React from 'react';
import { AbsoluteFill, Sequence, staticFile, useCurrentFrame, spring, useVideoConfig } from 'remotion';
import { Typewriter } from '@templates/elements/typography/typewriter/Typewriter';
import { TextReveal } from '@templates/elements/typography/text-reveal';

export const Scene2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Pop Reveal for the icon
  const iconScale = spring({
    fps,
    frame: frame - 10,
    config: { damping: 12, mass: 1, stiffness: 100 }
  });

  // Ring rotation
  const ringRotation = frame * 2;

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
      
      {/* 3D Python Icon with glowing rings */}
      <Sequence from={10} durationInFrames={94}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', top: '-100px' }}>
          
          {/* Cyberpunk Glowing Ring */}
          <div style={{
            position: 'absolute',
            width: '300px',
            height: '300px',
            borderRadius: '50%',
            border: '2px dashed rgba(0, 229, 255, 0.5)',
            boxShadow: '0 0 40px rgba(0, 229, 255, 0.2)',
            transform: `scale(${iconScale}) rotate(${ringRotation}deg)`
          }} />
          
          <div style={{
            position: 'absolute',
            width: '260px',
            height: '260px',
            borderRadius: '50%',
            border: '4px solid rgba(255, 215, 0, 0.3)', // Python Yellow accent
            transform: `scale(${iconScale}) rotate(-${ringRotation}deg)`
          }} />

          {/* Python Icon */}
          <img 
            src={staticFile('media/icon_python.svg')} 
            style={{ 
              width: '180px', 
              height: '180px', 
              transform: `scale(${iconScale})`,
              filter: 'drop-shadow(0px 0px 20px rgba(0, 229, 255, 0.6))'
            }} 
          />
        </AbsoluteFill>
      </Sequence>

      {/* Subtitle */}
      <Sequence from={15} durationInFrames={89}>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', top: '250px' }}>
          <div style={{ direction: 'rtl' }}>
            <Typewriter
              text="وسأعطيك خططاً لتعلم البرمجة"
              delay={0}
              duration={45}
              cursor={true}
              cursorColor="#00e5ff"
              color="#ffffff"
              fontSize={55}
              fontFamily="Alexandria"
              fontWeight="bold"
            />
          </div>
        </AbsoluteFill>
      </Sequence>

    </AbsoluteFill>
  );
};
