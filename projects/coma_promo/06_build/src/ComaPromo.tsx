import React from "react";
import { AbsoluteFill, Sequence, Video, Audio, staticFile, interpolate } from "remotion";
import CinematicText from "./CinematicText";
import { FadeOut } from "./FadeOut";

export const ComaPromo: React.FC = () => {
  const VIDEO_DURATION = 335; // 11.169s * 30fps
  const TRANSITION_DURATION = 30; // 1s overlap for smoother cross-dissolve

  return (
    <AbsoluteFill style={{ backgroundColor: "#FFD700" }}>
      <style>
        {`
          @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@700;800&display=swap');
        `}
      </style>

      {/* Global Background Music */}
      <Audio 
        src={staticFile("media/bgm2.mp3")}
        volume={(f) =>
          interpolate(f, [181, 211], [0.2, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })
        }
      />
      
      {/* Scene 0: Desktop Video */}
      <Sequence from={0} durationInFrames={VIDEO_DURATION}>
        <FadeOut durationInFrames={TRANSITION_DURATION}>
          <Video 
            src={staticFile("media/0825.mp4")}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
            volume={(f) =>
              interpolate(f, [181, 211], [1, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            }
          />
        </FadeOut>
      </Sequence>

      {/* Scene 1: First text (overlapped by TRANSITION_DURATION) */}
      <Sequence 
        from={VIDEO_DURATION - TRANSITION_DURATION} 
        durationInFrames={90 + TRANSITION_DURATION} // 120 frames
      >
        <FadeOut durationInFrames={TRANSITION_DURATION}>
          <CinematicText
            text="حِملك ثقيل ومحتاج تركيز؟"
            color="#000000"
            fontSize="8.5rem"
            fontFamily="'Tajawal', sans-serif"
          />
        </FadeOut>
      </Sequence>

      {/* Scene 2: Second text (starts overlapping the end of Scene 1, lasts till the end) */}
      <Sequence 
        from={VIDEO_DURATION - TRANSITION_DURATION + 90} // 335 - 30 + 90 = 395
        durationInFrames={120} // 395 + 120 = 515 (End of video)
      >
        {/* No FadeOut needed for the final scene, ends with the video */}
        <CinematicText
          text={
            <span style={{ display: "flex", alignItems: "center", gap: "2rem", justifyContent: "center", flexWrap: "wrap" }}>
              <span>مساحة عمل</span>
              <img 
                src={staticFile("media/CoMa.svg")} 
                alt="CoMa Logo" 
                style={{ 
                  height: "12rem", 
                  filter: "drop-shadow(0px 0px 20px rgba(0,0,0,0.5))",
                  transform: "scale(1.1)"
                }} 
              />
              <span>هي بيئتك المثالية للإنجاز</span>
            </span>
          }
          color="#000000"
          fontSize="9.5rem"
          fontFamily="'Tajawal', sans-serif"
        />
      </Sequence>
    </AbsoluteFill>
  );
};
