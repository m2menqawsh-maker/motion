import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
  Audio,
  Img,
  Sequence,
} from "remotion";
import { UnifiedCyberBackground } from "./UnifiedCyberBackground";

export const SCENE_4_DURATION_FRAMES = 251; // 15.50s - 23.88s @ 30fps (8.38s)

export const Scene4OOP: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // -------------------------------------------------------------
  // 1. Dynamic Camera Movement & Whip Pan
  // -------------------------------------------------------------
  // Whip Pan Entrance (f0 - f14)
  const whipPanX = interpolate(frame, [0, 14], [1080, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Camera Scale & Pan - keep it steady and centered to emphasize symmetry
  const cameraScale = interpolate(
    frame,
    [0, 20, 110, 160, 200, 251],
    [0.94, 1.0, 1.01, 1.0, 1.0, 0.98],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const cameraPanY = interpolate(
    frame,
    [0, 40, 115, 163, 188, 251],
    [0, 0, -10, -25, -35, -35],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // -------------------------------------------------------------
  // 2. Stage 1: Hero Header & Golden Shine Sweep
  // -------------------------------------------------------------
  const heroSpring = spring({ frame, fps, config: { stiffness: 140, damping: 18 } });

  const shineProgress = interpolate(frame, [25, 65], [-100, 200], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // -------------------------------------------------------------
  // 3. Stage 2: Symmetrical Pyramid Cards
  // -------------------------------------------------------------
  // Syncing with VO exactly:
  // "برمجة كائنية" (OOP) -> frame 115
  // "هياكل بيانات" (DS) -> frame 163
  // "وكود نظيف" (Clean Code) -> frame 188

  const card1Spring = spring({ frame: frame - 115, fps, config: { stiffness: 150, damping: 16 } });
  const card2Spring = spring({ frame: frame - 163, fps, config: { stiffness: 150, damping: 16 } });
  const card3Spring = spring({ frame: frame - 188, fps, config: { stiffness: 150, damping: 16 } });

  // Exit transition to Scene 5
  const exitSlide = interpolate(frame, [238, 251], [0, -1080], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        fontFamily: "'Alexandria', 'IBM Plex Sans Arabic', sans-serif",
        transform: `translateX(${whipPanX + exitSlide}px)`,
      }}
    >
      {/* Standalone Background */}
      {includeGlobalAudio && <UnifiedCyberBackground />}

      {/* Global Audio */}
      {includeGlobalAudio && (
        <>
          <Audio
            src={staticFile("media/vo_audio.wav")}
            startFrom={465}
            volume={1.0}
          />
          <Audio
            src={staticFile("media/bg_music.wav")}
            startFrom={465}
            volume={0.16}
          />
        </>
      )}

      {/* SFX Tracks */}
      <Sequence from={0} durationInFrames={25} name="SFX Whip Pan">
        <Audio src={staticFile("media/sfx_whoosh.wav")} volume={0.9} />
      </Sequence>
      <Sequence from={25} durationInFrames={35} name="SFX Golden Shine">
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={115} durationInFrames={30} name="SFX OOP Card">
        <Audio src={staticFile("media/sfx_pop.wav")} volume={0.9} />
      </Sequence>
      <Sequence from={163} durationInFrames={30} name="SFX DS Card">
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.9} />
      </Sequence>
      <Sequence from={188} durationInFrames={40} name="SFX Clean Code Card">
        <Audio src={staticFile("media/sfx_notification.wav")} volume={1.0} />
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
          padding: "160px 45px 65px 45px", // Moved header down significantly to center the scene
          boxSizing: "border-box",
          transform: `translateY(${cameraPanY}px) scale(${cameraScale})`,
          transformOrigin: "50% 50%",
        }}
      >
        {/* ========================================================= */}
        {/* TOP HEADER: Centered & Perfectly Symmetrical */}
        {/* ========================================================= */}
        <div
          style={{
            zIndex: 30,
            direction: "rtl",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 40,
            width: "100%",
            textAlign: "center",
            transform: `scale(${heroSpring})`,
            marginBottom: 60, // Space between header and pyramid cards
          }}
        >
          {/* Phase 2 Pill */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 16,
              padding: "16px 50px",
              borderRadius: 50,
              background: "rgba(18, 10, 38, 0.96)",
              border: "3px solid #BD00FF",
              boxShadow: "0 0 45px rgba(189, 0, 255, 0.6)",
            }}
          >
            <span style={{ fontSize: 36 }}>⚡</span>
            <span
              style={{
                fontSize: 34,
                fontWeight: 950,
                color: "#E085FF",
                letterSpacing: 2,
                textShadow: "0 0 20px #BD00FF",
              }}
            >
              المرحلة الثانية • الأيام 11 إلى 20
            </span>
            <span style={{ fontSize: 36, transform: "scaleX(-1)" }}>⚡</span> {/* Symmetrical icon */}
          </div>

          {/* Golden Shine Title */}
          <div
            style={{
              fontSize: 66,
              fontWeight: 950,
              color: "#FFFFFF",
              textShadow: "0 0 35px rgba(255,255,255,0.6)",
              lineHeight: 1.3,
            }}
          >
            هون{" "}
            <span
              style={{
                position: "relative",
                display: "inline-block",
                color: "#FFE600",
                textShadow:
                  "0 0 40px rgba(255, 230, 0, 0.9), 0 0 15px #FF8800",
                backgroundImage:
                  "linear-gradient(110deg, #FFD700 0%, #FFFFFF 50%, #FF9500 100%)",
                backgroundSize: "200% 100%",
                backgroundPosition: `${shineProgress}% 0`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              الشـغـل الحـقـيـقـي
            </span>{" "}
            يبدأ! 🚀
          </div>
        </div>

        {/* ========================================================= */}
        {/* CENTER ARENA: Symmetrical Pyramid Layout (1 Wide, 2 Squares) */}
        {/* ========================================================= */}
        <div
          style={{
            position: "relative",
            width: "100%",
            maxWidth: 960,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 40,
            direction: "rtl",
          }}
        >
          {/* CARD 3: Clean Code (Wide Banner - Green) - Tops the pyramid at f188 */}
          <div
            style={{
              width: "100%",
              height: 320,
              borderRadius: 36,
              background: "rgba(8, 36, 24, 0.95)",
              border: "4px solid #00FFA3",
              boxShadow:
                "0 0 60px rgba(0, 255, 163, 0.4), inset 0 0 30px rgba(0, 255, 163, 0.15)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "30px 40px",
              boxSizing: "border-box",
              overflow: "hidden",
              transform: `scale(${card3Spring})`,
              position: "relative",
              textAlign: "center",
            }}
          >
            {/* Top Accent Line for Symmetry */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: "10%",
                right: "10%",
                height: 6,
                background: "linear-gradient(90deg, transparent, #00FFA3, #00C882, #00FFA3, transparent)",
                boxShadow: "0 0 20px #00FFA3",
              }}
            />

            {/* Badge Icon (Centered) */}
            <div
              style={{
                width: 90,
                height: 90,
                borderRadius: 25,
                background: "rgba(0, 255, 163, 0.2)",
                border: "2px solid #00FFA3",
                boxShadow: "0 0 25px rgba(0, 255, 163, 0.6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 16,
              }}
            >
              <Img
                src={staticFile("media/icon_check.svg")}
                style={{ width: 55, height: 55, filter: "drop-shadow(0 0 10px #00FFA3)" }}
              />
            </div>

            {/* Title */}
            <div
              style={{
                fontSize: 42,
                fontWeight: 950,
                color: "#FFFFFF",
                textShadow: "0 0 25px rgba(255,255,255,0.5)",
                marginBottom: 8,
              }}
            >
              3. كود نظيف زي المحترفين
            </div>

            {/* Code Snippet (Centered) */}
            <div
              style={{
                padding: "8px 24px",
                borderRadius: 16,
                background: "rgba(0, 0, 0, 0.85)",
                border: "2px solid rgba(0, 255, 163, 0.5)",
                color: "#00F2FE",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 22,
                fontWeight: 800,
                display: "inline-block",
              }}
            >
              0 Errors • PEP 8 • Clean Architecture
            </div>
          </div>

          {/* Row 2: OOP (Square) & DS (Square) */}
          <div
            style={{
              display: "flex",
              width: "100%",
              justifyContent: "space-between",
              gap: 40,
            }}
          >
            {/* CARD 1: OOP (Square - Purple) - Base Right at f115 */}
            <div
              style={{
                flex: 1,
                height: 380,
                borderRadius: 36,
                background: "rgba(18, 10, 36, 0.95)",
                border: "4px solid #BD00FF",
                boxShadow:
                  "0 0 60px rgba(189, 0, 255, 0.4), inset 0 0 30px rgba(189, 0, 255, 0.15)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "30px 20px",
                boxSizing: "border-box",
                overflow: "hidden",
                transform: `scale(${card1Spring})`,
                position: "relative",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: "20%",
                  right: "20%",
                  height: 6,
                  background: "linear-gradient(90deg, transparent, #BD00FF, #E085FF, #BD00FF, transparent)",
                  boxShadow: "0 0 20px #BD00FF",
                }}
              />
              
              <div
                style={{
                  width: 100,
                  height: 100,
                  borderRadius: 25,
                  background: "rgba(189, 0, 255, 0.2)",
                  border: "2px solid #BD00FF",
                  boxShadow: "0 0 25px rgba(189, 0, 255, 0.6)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 20,
                }}
              >
                <Img
                  src={staticFile("media/icon_python.svg")}
                  style={{ width: 60, height: 60 }}
                />
              </div>

              <div
                style={{
                  fontSize: 36,
                  fontWeight: 950,
                  color: "#FFFFFF",
                  textShadow: "0 0 25px rgba(255,255,255,0.5)",
                  marginBottom: 12,
                  lineHeight: 1.3,
                }}
              >
                1. برمجة كائنية
              </div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: "#E085FF",
                  lineHeight: 1.4,
                  marginBottom: 20,
                  padding: "0 10px",
                }}
              >
                بناء فئات لكود منظم وقوي
              </div>
              <div
                style={{
                  padding: "8px 16px",
                  borderRadius: 16,
                  background: "rgba(0, 0, 0, 0.85)",
                  border: "2px solid rgba(189, 0, 255, 0.5)",
                  color: "#00F2FE",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 18,
                  fontWeight: 800,
                }}
              >
                class System(App):
              </div>
            </div>

            {/* CARD 2: Data Structures (Square - Cyan) - Base Left at f163 */}
            <div
              style={{
                flex: 1,
                height: 380,
                borderRadius: 36,
                background: "rgba(8, 24, 44, 0.95)",
                border: "4px solid #00F2FE",
                boxShadow:
                  "0 0 60px rgba(0, 242, 254, 0.4), inset 0 0 30px rgba(0, 242, 254, 0.15)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "30px 20px",
                boxSizing: "border-box",
                overflow: "hidden",
                transform: `scale(${card2Spring})`,
                position: "relative",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: "20%",
                  right: "20%",
                  height: 6,
                  background: "linear-gradient(90deg, transparent, #00F2FE, #4FACFE, #00F2FE, transparent)",
                  boxShadow: "0 0 20px #00F2FE",
                }}
              />
              
              <div
                style={{
                  width: 100,
                  height: 100,
                  borderRadius: 25,
                  background: "rgba(0, 242, 254, 0.2)",
                  border: "2px solid #00F2FE",
                  boxShadow: "0 0 25px rgba(0, 242, 254, 0.6)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 20,
                }}
              >
                <Img
                  src={staticFile("media/icon_database.svg")}
                  style={{ width: 60, height: 60 }}
                />
              </div>

              <div
                style={{
                  fontSize: 36,
                  fontWeight: 950,
                  color: "#FFFFFF",
                  textShadow: "0 0 25px rgba(255,255,255,0.5)",
                  marginBottom: 12,
                  lineHeight: 1.3,
                }}
              >
                2. هياكل البيانات
              </div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: "#79C0FF",
                  lineHeight: 1.4,
                  marginBottom: 20,
                  padding: "0 10px",
                }}
              >
                تنظيم البيانات بكفاءة وسرعة
              </div>
              <div
                style={{
                  padding: "8px 16px",
                  borderRadius: 16,
                  background: "rgba(0, 0, 0, 0.85)",
                  border: "2px solid rgba(0, 242, 254, 0.5)",
                  color: "#00FFA3",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 18,
                  fontWeight: 800,
                }}
              >
                Stack • Queue
              </div>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

