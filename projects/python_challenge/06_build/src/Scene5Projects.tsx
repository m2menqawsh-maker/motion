import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  Audio,
  Sequence,
} from "remotion";
import { UnifiedCyberBackground } from "./UnifiedCyberBackground";

export const SCENE_5_DURATION_FRAMES = 133; // 23.88s - 28.28s @ 30fps

export const Scene5Projects: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // -------------------------------------------------------------
  // 1. Camera Animation: Zoom-Out and Curved Path Follow
  // -------------------------------------------------------------
  // Entrance (f0 - f20): Fast slide up from Scene 4
  const entranceY = interpolate(frame, [0, 15], [1080, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Zoom out to reveal the "Roadmap"
  const cameraScale = interpolate(frame, [10, 60], [2.5, 1.0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Pan across the roadmap curve (simulating following a path)
  const cameraPanX = interpolate(frame, [10, 80], [-400, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const cameraPanY = interpolate(frame, [10, 80], [300, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // -------------------------------------------------------------
  // 2. Roadmap SVG Animation
  // -------------------------------------------------------------
  // The path drawn progressively
  const pathDrawProgress = spring({
    frame: frame - 15,
    fps,
    config: { stiffness: 60, damping: 14 }, // Slower draw
  });
  const pathLength = 1500; // Approx length of SVG path
  const strokeDashoffset = pathLength - pathDrawProgress * pathLength;

  // Nodes popping up on the roadmap
  const node1Spring = spring({ frame: frame - 20, fps, config: { stiffness: 150, damping: 15 } });
  const node2Spring = spring({ frame: frame - 40, fps, config: { stiffness: 150, damping: 15 } });
  const node3Spring = spring({ frame: frame - 60, fps, config: { stiffness: 150, damping: 15 } });

  // -------------------------------------------------------------
  // 3. Main Text Animation ("مشاريع حقيقية")
  // -------------------------------------------------------------
  // Synced with VO: "بتوصل لمشاريع حقيقية" starts around ~26.96s -> Local frame ~92
  const textEntrance = spring({
    frame: frame - 60, // Start growing slightly before the word to fill screen
    fps,
    config: { stiffness: 80, damping: 15 },
  });

  // Slowly grows to fill the center of the view
  const textScale = interpolate(frame, [60, 133], [0, 1.4], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const textOpacity = interpolate(frame, [60, 75], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        fontFamily: "'Alexandria', 'IBM Plex Sans Arabic', sans-serif",
        transform: `translateY(${entranceY}px)`, // Scene 5 slides up
      }}
    >
      {/* Standalone Background */}
      {includeGlobalAudio && <UnifiedCyberBackground />}

      {/* Global Audio */}
      {includeGlobalAudio && (
        <>
          <Audio
            src={staticFile("media/vo_audio.wav")}
            startFrom={716} // 23.88s * 30fps = 716
            volume={1.0}
          />
          <Audio
            src={staticFile("media/bg_music.wav")}
            startFrom={716}
            volume={0.16}
          />
        </>
      )}

      {/* SFX Tracks */}
      <Sequence from={0} durationInFrames={30} name="SFX Transition">
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={20} durationInFrames={20} name="SFX Node 1">
        <Audio src={staticFile("media/sfx_pop.wav")} volume={0.5} />
      </Sequence>
      <Sequence from={40} durationInFrames={20} name="SFX Node 2">
        <Audio src={staticFile("media/sfx_pop.wav")} volume={0.5} />
      </Sequence>
      <Sequence from={77}>
        <Audio src={staticFile("media/sfx_pop.wav")} volume={0.9} />
      </Sequence>

      {/* Main Interactive Screen Canvas */}
      <div
        style={{
          position: "relative",
          zIndex: 10,
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          transform: `scale(${cameraScale}) translate(${cameraPanX}px, ${cameraPanY}px)`,
          transformOrigin: "50% 50%",
        }}
      >
        {/* ========================================================= */}
        {/* TOP HEADER: Phase 3 Banner */}
        {/* ========================================================= */}
        <div
          style={{
            zIndex: 30,
            marginTop: 100,
            transform: `scale(${spring({ frame: frame - 15, fps, config: { stiffness: 120, damping: 15 } })})`,
          }}
        >
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 16,
              padding: "16px 50px",
              borderRadius: 50,
              background: "rgba(18, 10, 38, 0.96)",
              border: "3px solid #00F2FE",
              boxShadow: "0 0 45px rgba(0, 242, 254, 0.6)",
              direction: "rtl",
            }}
          >
            <span style={{ fontSize: 36 }}>🔥</span>
            <span
              style={{
                fontSize: 34,
                fontWeight: 950,
                color: "#79C0FF",
                letterSpacing: 2,
                textShadow: "0 0 20px #00F2FE",
              }}
            >
              المرحلة الثالثة • الأيام 21 إلى 30
            </span>
            <span style={{ fontSize: 36, transform: "scaleX(-1)" }}>🔥</span>
          </div>
        </div>

        {/* ========================================================= */}
        {/* ROADMAP SVG (Curved Path) */}
        {/* ========================================================= */}
        <div
          style={{
            position: "absolute",
            top: 250, // Moved up to free the center/bottom space
            left: 0,
            width: "100%",
            height: 600,
            zIndex: 15,
            opacity: interpolate(frame, [10, 20], [0, 1]),
          }}
        >
          <svg
            width="1080"
            height="600"
            viewBox="0 0 1080 600"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M 150,500 C 400,500 300,300 540,300 C 780,300 700,100 950,100"
              stroke="url(#paint0_linear)"
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={pathLength}
              strokeDashoffset={strokeDashoffset}
              style={{ filter: "drop-shadow(0 0 20px #00F2FE)" }}
            />
            <defs>
              <linearGradient id="paint0_linear" x1="150" y1="500" x2="950" y2="100" gradientUnits="userSpaceOnUse">
                <stop stopColor="#BD00FF" />
                <stop offset="0.5" stopColor="#00F2FE" />
                <stop offset="1" stopColor="#00FFA3" />
              </linearGradient>
            </defs>
          </svg>

          {/* Roadmap Nodes with Project Emojis */}
          {/* Node 1: Telegram Bot */}
          <div
            style={{
              position: "absolute",
              top: 470, // 500 - 30
              left: 120, // 150 - 30
              width: 60,
              height: 60,
              borderRadius: "50%",
              background: "rgba(189, 0, 255, 0.2)",
              border: "4px solid #BD00FF",
              boxShadow: "0 0 30px #BD00FF, inset 0 0 15px #BD00FF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 32,
              transform: `scale(${node1Spring})`,
            }}
          >
            🤖
          </div>
          {/* Node 2: APIs */}
          <div
            style={{
              position: "absolute",
              top: 270, // 300 - 30
              left: 510, // 540 - 30
              width: 60,
              height: 60,
              borderRadius: "50%",
              background: "rgba(0, 242, 254, 0.2)",
              border: "4px solid #00F2FE",
              boxShadow: "0 0 30px #00F2FE, inset 0 0 15px #00F2FE",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 32,
              transform: `scale(${node2Spring})`,
            }}
          >
            🌐
          </div>
          {/* Node 3: Automation */}
          <div
            style={{
              position: "absolute",
              top: 70, // 100 - 30
              left: 920, // 950 - 30
              width: 60,
              height: 60,
              borderRadius: "50%",
              background: "rgba(0, 255, 163, 0.2)",
              border: "4px solid #00FFA3",
              boxShadow: "0 0 30px #00FFA3, inset 0 0 15px #00FFA3",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 32,
              transform: `scale(${node3Spring})`,
            }}
          >
            ⚙️
          </div>
        </div>

        {/* ========================================================= */}
        {/* MAIN TEXT: "مشاريع حقيقية" */}
        {/* ========================================================= */}
        <div
          style={{
            position: "absolute",
            top: 900, // Pushed way down so it doesn't touch the roadmap at all
            width: "100%",
            textAlign: "center",
            zIndex: 40,
            opacity: textOpacity,
            transform: `scale(${textScale * textEntrance})`,
          }}
        >
          <div
            style={{
              fontSize: 140, // Very large to fill center bottom
              fontWeight: 950,
              color: "#FFFFFF",
              textShadow: "0 0 60px rgba(255,255,255,0.7), 0 0 20px #00F2FE",
              lineHeight: 1.2,
              direction: "rtl",
            }}
          >
            مشاريع{" "}
            <span
              style={{
                color: "#FFE600",
                textShadow: "0 0 50px rgba(255, 230, 0, 0.8)",
              }}
            >
              حقيقية
            </span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
