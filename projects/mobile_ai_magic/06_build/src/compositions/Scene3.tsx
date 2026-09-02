import React from 'react';
import { AbsoluteFill, Sequence, useVideoConfig, useCurrentFrame, Audio, staticFile } from 'remotion';
import { TrackingIn } from '@/templates/elements/typography/tracking-in/TrackingIn';
import { loadFont } from "@remotion/google-fonts/Cairo";
import { ClaudeCode } from '@/remotion/scenes/claude-code';

const { fontFamily } = loadFont();

export const Scene3: React.FC = () => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#111' }}>
      
      <Audio src={staticFile('media/sentence_003_norm.wav')} />
      <Sequence from={5}>
        <Audio src={staticFile('media/keyboard_norm.wav')} volume={0.5} />
      </Sequence>
      
      {/* Claude Code Terminal */}
      <Sequence from={0}>
        <div style={{ transform: 'scale(1.2)', transformOrigin: 'center center', width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <ClaudeCode 
            title="Claude Code v2.0"
            userName="Momen"
            prompt="bootstrap a full-stack project from my idea"
            theme="dark"
            accentColor="#D97757"
          />
        </div>
      </Sequence>

      {/* Typography Overlay */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        width: '100%',
        height: '100%',
        color: 'white',
        fontFamily,
        pointerEvents: 'none',
        zIndex: 10
      }}>
        
        <Sequence from={20}>
          <div style={{ position: 'absolute', top: '20%', width: '100%', display: 'flex', justifyContent: 'center', direction: 'rtl', willChange: 'transform' }}>
            <TrackingIn 
              text="الذكاء الاصطناعي اليوم" 
              delay={0} 
              duration={15} 
              color="#fff" 
              fromTracking={0.2} 
              tracking={0} 
              blur={true} 
              fontSize={90} 
              fontWeight="900" 
            />
          </div>
        </Sequence>
        
        <Sequence from={55}>
          <div style={{ position: 'absolute', top: '75%', width: '100%', display: 'flex', justifyContent: 'center', direction: 'rtl', willChange: 'transform', backgroundColor: 'rgba(0,0,0,0.6)', padding: '20px 40px', borderRadius: '40px', border: '2px solid #D97757' }}>
            <TrackingIn 
              text="بحوّل فكرتك لمشروع حقيقي!" 
              delay={0} 
              duration={20} 
              color="#D97757" 
              fromTracking={0.1} 
              tracking={0} 
              blur={true} 
              fontSize={80} 
              fontWeight="900" 
            />
          </div>
        </Sequence>
      </div>
    </AbsoluteFill>
  );
};
