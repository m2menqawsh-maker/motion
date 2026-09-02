import React from 'react';
import { AbsoluteFill, Img, Sequence, Audio, staticFile } from 'remotion';
import { Pulse } from '@/engine/primitives/Pulse';
import { Enter } from '@/engine/primitives/Enter';
import { PhoneFrame } from '@/components/snap-cn/phone-frame';

const ReelsUI: React.FC = () => {
  return (
    <AbsoluteFill style={{ pointerEvents: 'none', color: 'white', fontFamily: 'Inter, sans-serif' }}>
      {/* Right Column Icons */}
      <div style={{ position: 'absolute', right: 10, bottom: 80, display: 'flex', flexDirection: 'column', gap: 18, alignItems: 'center' }}>
        {/* Heart */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.7 0l-1.1 1-1.1-1a5.5 5.5 0 0 0-7.8 7.8l1 1 7.9 7.9 7.9-7.9 1-1a5.5 5.5 0 0 0 0-7.8z"></path></svg>
          <span style={{ fontSize: 10, fontWeight: 600, textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>1.2M</span>
        </div>
        {/* Comment */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
          <span style={{ fontSize: 10, fontWeight: 600, textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>4,532</span>
        </div>
        {/* Share */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          <span style={{ fontSize: 10, fontWeight: 600, textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>12K</span>
        </div>
        {/* More */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
           <svg width="24" height="24" viewBox="0 0 24 24" fill="white"><circle cx="12" cy="12" r="2"/><circle cx="12" cy="5" r="2"/><circle cx="12" cy="19" r="2"/></svg>
        </div>
        {/* Audio thumbnail */}
        <div style={{ width: 28, height: 28, borderRadius: 6, border: '2px solid white', overflow: 'hidden', marginTop: 10 }}>
          <div style={{ backgroundColor: '#333', width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
          </div>
        </div>
      </div>

      {/* Bottom Profile & Caption */}
      <div style={{ position: 'absolute', left: 16, bottom: 20, right: 50, display: 'flex', flexDirection: 'column', gap: 8 }}>
         {/* User Info */}
         <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 28, height: 28, borderRadius: '50%', backgroundColor: 'white', padding: 1.5 }}>
               <div style={{ width: '100%', height: '100%', borderRadius: '50%', backgroundColor: '#666', overflow: 'hidden', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                 <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
               </div>
            </div>
            <span style={{ fontSize: 13, fontWeight: 600, textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>tech_expert</span>
            <div style={{ padding: '2px 8px', borderRadius: 4, border: '1px solid white', fontSize: 11, fontWeight: 600, marginLeft: 4 }}>Follow</div>
         </div>
         {/* Caption */}
         <div style={{ fontSize: 12, fontWeight: 400, textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>
            الموبايل الي بايدك اقوى من كمبيوتر ناسا زمان! 🚀📱 #tech #nasa #space
         </div>
         {/* Audio Track */}
         <div style={{ display: 'flex', alignItems: 'center', gap: 4, opacity: 0.9 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="white"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
            <span style={{ fontSize: 11, textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>Original Audio - tech_expert</span>
         </div>
      </div>
    </AbsoluteFill>
  );
};

export const Scene1: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'black', justifyContent: 'center', alignItems: 'center' }}>
      
      {/* Voiceover and SFX */}
      <Audio src={staticFile('media/vo_1.wav')} />
      <Sequence from={1}>
        <Audio src={staticFile('media/sfx_whoosh.wav')} volume={0.6} />
      </Sequence>
      <Sequence from={49}>
        <Audio src={staticFile('media/sfx_swoosh.wav')} volume={0.6} />
      </Sequence>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
        {/* Shot 1: The smartphone */}
        <Enter scaleFrom={0.5} translateY={50} duration={15} delay={1}>
           <PhoneFrame variant="showcase" scale={1.2}>
             <AbsoluteFill style={{ backgroundColor: '#000011', justifyContent: 'center', alignItems: 'center' }}>
                <Pulse count={3} delay={5} intensity={1.1} period={10}>
                  <Img 
                    src={staticFile('media/icon_mobile.svg')} 
                    width={150} 
                    style={{ filter: 'drop-shadow(0 0 20px #00FFFF)' }} 
                  />
                </Pulse>
                <ReelsUI />
             </AbsoluteFill>
           </PhoneFrame>
        </Enter>

        {/* Shot 2: NASA Computer appears floating below or beside */}
        <Sequence from={49}>
          <Enter scaleFrom={0.5} translateY={30} duration={12}>
             <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px 32px', borderRadius: 20, border: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 20 }}>
                <Img 
                  src={staticFile('media/icon_computer.svg')} 
                  width={60} 
                  style={{ filter: 'drop-shadow(0 0 20px #FF00FF)' }} 
                />
                <div style={{ color: 'white', fontFamily: 'Inter, sans-serif' }}>
                   <div style={{ fontSize: 20, fontWeight: 'bold' }}>NASA 1969 Computer</div>
                   <div style={{ fontSize: 14, color: '#aaa' }}>Apollo Guidance Computer</div>
                </div>
             </div>
          </Enter>
        </Sequence>
      </div>

    </AbsoluteFill>
  );
};
