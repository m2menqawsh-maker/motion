import React from 'react';
import { AbsoluteFill, Sequence, useVideoConfig, useCurrentFrame, spring, interpolate, OffthreadVideo, Audio, staticFile } from 'remotion';
import { TrackingIn } from '@/templates/elements/typography/tracking-in/TrackingIn';
import { C } from '@/engine/tokens';
import { loadFont } from "@remotion/google-fonts/Cairo";

const { fontFamily } = loadFont();

const PhoneMockup: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  
  // Enter at frame 1
  const progress = spring({
    frame: frame - 1,
    fps,
    config: { damping: 12 },
    durationInFrames: 30
  });
  
  const translateY = interpolate(progress, [0, 1], [1000, 0]);
  const scale = interpolate(progress, [0, 1], [0.8, 1]);

  return (
    <div style={{
      position: 'absolute',
      left: '50%',
      top: '50%',
      width: 900,
      height: 1700,
      marginLeft: -450,
      marginTop: -850,
      transform: `translateY(${translateY}px) scale(${scale})`,
      backgroundColor: '#111',
      borderRadius: 80,
      border: '24px solid #333',
      boxShadow: '0 40px 100px rgba(0,0,0,0.5)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white',
      fontFamily
    }}>
      {/* Notch */}
      <div style={{
        position: 'absolute',
        top: 0,
        width: 240,
        height: 60,
        backgroundColor: '#333',
        borderBottomLeftRadius: 30,
        borderBottomRightRadius: 30,
        zIndex: 10
      }} />
      {children}
    </div>
  );
};

export const Scene1: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      <OffthreadVideo 
        src={staticFile('media/bg_ai_final.mp4')} 
        style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.5 }} 
      />
      
      <Audio src={staticFile('media/sentence_001_norm.wav')} />
      <Sequence from={1}>
        <Audio src={staticFile('media/whoosh_norm.wav')} volume={0.5} />
      </Sequence>
      
      <PhoneMockup>
        <Sequence from={49}>
          <div style={{ position: 'absolute', top: '35%', width: '100%', display: 'flex', justifyContent: 'center', direction: 'rtl', willChange: 'transform' }}>
            <TrackingIn 
              text="أقوى" 
              delay={0} 
              duration={20} 
              color="#fff" 
              fromTracking={0.2} 
              tracking={0} 
              blur={true} 
              fontSize={180} 
              fontWeight="900" 
            />
          </div>
        </Sequence>
        
        <Sequence from={80}>
          <div style={{ position: 'absolute', top: '55%', width: '100%', display: 'flex', justifyContent: 'center', padding: '0 20px', boxSizing: 'border-box', direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
            <TrackingIn 
              text="من كمبيوترات ناسا" 
              delay={0} 
              duration={30} 
              color="#00ffcc" 
              fromTracking={0.1} 
              tracking={0} 
              blur={true} 
              fontSize={100} 
              fontWeight="900" 
              align="center"
            />
          </div>
        </Sequence>
      </PhoneMockup>
    </AbsoluteFill>
  );
};
