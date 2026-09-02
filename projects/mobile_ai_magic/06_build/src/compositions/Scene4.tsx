import React from 'react';
import { AbsoluteFill, Sequence, useVideoConfig, useCurrentFrame, spring, interpolate, Audio, staticFile } from 'remotion';
import { TrackingIn } from '@/templates/elements/typography/tracking-in/TrackingIn';
import { loadFont } from "@remotion/google-fonts/Cairo";

const { fontFamily } = loadFont();

const FollowButton: React.FC<{ progress: number, clickProgress: number }> = ({ progress, clickProgress }) => {
  const scaleIn = interpolate(progress, [0, 1], [0.5, 1], { extrapolateRight: 'clamp' });
  const clickScale = interpolate(clickProgress, [0, 0.5, 1], [1, 0.9, 1], { extrapolateRight: 'clamp' });
  const finalScale = scaleIn * clickScale;
  
  const bg = interpolate(clickProgress, [0, 1], [0, 1], { extrapolateRight: 'clamp' }) > 0.5 ? '#111' : '#007AFF';
  const color = interpolate(clickProgress, [0, 1], [0, 1], { extrapolateRight: 'clamp' }) > 0.5 ? '#fff' : '#fff';
  const border = interpolate(clickProgress, [0, 1], [0, 1], { extrapolateRight: 'clamp' }) > 0.5 ? '2px solid rgba(255,255,255,0.3)' : '2px solid transparent';
  const text = interpolate(clickProgress, [0, 1], [0, 1], { extrapolateRight: 'clamp' }) > 0.5 ? 'Following' : 'Follow';

  return (
    <div style={{
      transform: `scale(${finalScale})`,
      backgroundColor: bg,
      color: color,
      border: border,
      padding: '30px 80px',
      borderRadius: '60px',
      fontSize: 60,
      fontWeight: 'bold',
      display: 'flex',
      alignItems: 'center',
      gap: 20,
      boxShadow: '0 20px 50px rgba(0, 122, 255, 0.4)'
    }}>
      <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
      {text}
    </div>
  );
};

export const Scene4: React.FC = () => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  const btnIn = spring({ frame: frame - 45, fps, config: { damping: 12 }, durationInFrames: 30 });
  const btnClick = spring({ frame: frame - 75, fps, config: { damping: 12, mass: 0.5 }, durationInFrames: 15 });

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      <Audio src={staticFile('media/sentence_004_norm.wav')} />
      <Sequence from={40}>
        <Audio src={staticFile('media/swoosh_norm.wav')} volume={0.6} />
      </Sequence>
      <Sequence from={75}>
        <Audio src={staticFile('media/notification_norm.wav')} volume={0.5} />
      </Sequence>
      
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        width: '100%',
        height: '100%',
        color: 'white',
        fontFamily
      }}>
        
        <Sequence from={5}>
          <div style={{ position: 'absolute', top: '30%', width: '100%', display: 'flex', justifyContent: 'center', direction: 'rtl', willChange: 'transform' }}>
            <TrackingIn 
              text="إبدأ ابني وتابعني..." 
              delay={0} 
              duration={15} 
              color="#fff" 
              fromTracking={0.2} 
              tracking={0} 
              blur={true} 
              fontSize={100} 
              fontWeight="900" 
            />
          </div>
        </Sequence>
        
        <Sequence from={45}>
          <div style={{ position: 'absolute', top: '50%', width: '100%', display: 'flex', justifyContent: 'center' }}>
            <FollowButton progress={btnIn} clickProgress={btnClick} />
          </div>
        </Sequence>

        <Sequence from={90}>
          <div style={{ position: 'absolute', top: '75%', width: '100%', display: 'flex', justifyContent: 'center', direction: 'rtl', willChange: 'transform' }}>
            <TrackingIn 
              text="لنكمل مع بعض!" 
              delay={0} 
              duration={15} 
              color="#28C840" 
              fromTracking={0.1} 
              tracking={0} 
              blur={true} 
              fontSize={110} 
              fontWeight="900" 
            />
          </div>
        </Sequence>

      </div>
    </AbsoluteFill>
  );
};
