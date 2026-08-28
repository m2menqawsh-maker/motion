import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
  Audio,
  staticFile,
} from "remotion";

export const SCENE_7_DURATION_FRAMES = 242; // 15f extra start + 182f core + 45f extra end

export const Scene7Twist: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Part 1: "بس في سر واحد لازم تعرفه"
  // Starts at original 43 + 15 extra silence = 58
  const text1Opacity = interpolate(frame, [58, 63, 122, 127], [0, 1, 1, 0]);
  const text1Scale = interpolate(frame, [58, 127], [1, 1.1]);

  // Part 2: "إن الكورسات لحالها ما بتكفي"
  // Timing: Starts at original 112 + 15 = 127. "ما بتكفي" hits at original 165 + 15 = 180.
  const isPart2 = frame >= 127;
  
  // Shock Zoom at frame 180
  const shockZoomTrigger = frame - 180;
  const shockZoomScale = spring({
    frame: shockZoomTrigger,
    fps,
    config: { stiffness: 200, damping: 10 },
    from: 0,
    to: 1,
  });
  
  // Overall Scene Scale
  const sceneScale = interpolate(
    frame,
    [127, 179],
    [1, 1.05],
    { extrapolateRight: "clamp" }
  ) + (shockZoomScale * 0.2); // Add 0.2 scale sharply at frame 180

  // Red Strikethrough Line on "الكورسات"
  // Starts drawing at frame 180
  const strikeProgress = spring({
    frame: frame - 180,
    fps,
    config: { stiffness: 300, damping: 15 },
    from: 0,
    to: 1,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", fontFamily: "'Alexandria', sans-serif" }}>
      {/* Global Audio */}
      {includeGlobalAudio && (
        <>
          <Sequence from={15}>
            <Audio src={staticFile("media/vo_audio.wav")} startFrom={998} endAt={1180} volume={1.0} />
          </Sequence>
          {/* Mute BGM slightly more for dramatic tension */}
          <Audio src={staticFile("media/bg_music.wav")} startFrom={998} volume={0.05} />
        </>
      )}

      {/* Part 1: "بس في سر واحد لازم تعرفه" */}
      <Sequence from={58} durationInFrames={69}>
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <div
            style={{
              opacity: text1Opacity,
              transform: `scale(${text1Scale})`,
              color: "white",
              fontSize: 80,
              fontWeight: 900,
              textAlign: "center",
              lineHeight: 1.5,
              width: "80%",
            }}
          >
            بس في <span style={{ color: "#FFE600" }}>سر واحد</span> لازم تعرفه..
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Part 2: "إن الكورسات لحالها ما بتكفي" */}
      <Sequence from={127} durationInFrames={115}>
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", transform: `scale(${sceneScale})` }}>
          
          <div
            style={{
              color: "white",
              fontSize: 90,
              fontWeight: 900,
              textAlign: "center",
              lineHeight: 1.6,
              width: "90%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 20
            }}
          >
            {/* Top row */}
            <div style={{ display: "flex", gap: 20, direction: "rtl" }}>
              <span style={{ opacity: interpolate(frame, [127, 132], [0, 1]) }}>إن</span>
              
              {/* "الكورسات" with strikethrough */}
              <div style={{ position: "relative" }}>
                <span style={{ 
                  color: frame >= 180 ? "#666" : "white", 
                  transition: "color 0.2s" 
                }}>
                  الكورسات
                </span>
                
                {/* The Red Strike */}
                {frame >= 180 && (
                  <div
                    style={{
                      position: "absolute",
                      top: "50%",
                      left: "-5%",
                      width: `${strikeProgress * 110}%`,
                      height: 15,
                      backgroundColor: "#FF004D",
                      transform: "translateY(-50%) rotate(-5deg)",
                      boxShadow: "0 0 20px rgba(255, 0, 77, 0.8)",
                      borderRadius: 10,
                    }}
                  />
                )}
              </div>
              
              <span style={{ opacity: interpolate(frame, [142, 147], [0, 1]) }}>لحالها</span>
            </div>

            {/* Bottom row: "ما بتكفي" */}
            <div
              style={{
                color: "#FF004D",
                fontSize: 120,
                opacity: interpolate(frame, [180, 183], [0, 1]),
                transform: `scale(${spring({ frame: frame - 180, fps, from: 0.5, to: 1 })})`,
                textShadow: "0 0 40px rgba(255, 0, 77, 0.6)"
              }}
            >
              ما بتكفي!
            </div>

          </div>
        </AbsoluteFill>
      </Sequence>
      
      {/* Dramatic SFX */}
      <Sequence from={180}>
        <Audio src={staticFile("media/sfx_boom_impact.wav")} volume={1} />
        <Audio src={staticFile("media/sfx_swish_metal.wav")} volume={0.8} />
      </Sequence>
    </AbsoluteFill>
  );
};
