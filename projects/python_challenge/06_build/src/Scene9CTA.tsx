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

export const SCENE_9_DURATION_FRAMES = 255;

export const Scene9CTA: React.FC<{ includeGlobalAudio?: boolean }> = ({
  includeGlobalAudio = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Intro Sequence (36 - 85)
  const introScale = spring({
    frame: frame - 36,
    fps,
    config: { stiffness: 150, damping: 10 },
    from: 0.5,
    to: 1,
  });

  // Bookmark Sequence (85 - 124)
  const bookmarkClick = spring({
    frame: frame - 100, // Click happens a bit after it appears
    fps,
    config: { stiffness: 300, damping: 10 },
    from: 1,
    to: 0.8,
  });
  const bookmarkScale = spring({
    frame: frame - 85,
    fps,
    config: { stiffness: 200, damping: 12 },
    from: 0,
    to: 1,
  }) * (frame >= 100 ? bookmarkClick : 1) * (frame >= 105 ? 1 / bookmarkClick : 1); // Simulate click down and release

  // Laptop Sequence (124 - 151)
  const laptopOpen = spring({
    frame: frame - 124,
    fps,
    config: { stiffness: 120, damping: 14 },
    from: 0,
    to: 1,
  });

  // Typing Sequence (151 - 225)
  const codeText = 'print("Hello World")';
  const typingFrame = Math.max(0, frame - 151);
  const charsToShow = Math.floor(typingFrame / 2); // 1 char every 2 frames
  const displayedCode = codeText.substring(0, charsToShow);

  // Finale Sequence (225 - 255)
  const finaleZoom = spring({
    frame: frame - 225,
    fps,
    config: { stiffness: 100, damping: 14 },
    from: 0,
    to: 1,
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", fontFamily: "'Alexandria', 'JetBrains Mono', sans-serif" }}>
      {/* Global Audio for Standalone */}
      {includeGlobalAudio && (
        <>
          <Audio src={staticFile("media/vo_audio.wav")} startFrom={1308} volume={1.0} />
          <Audio src={staticFile("media/bg_music.wav")} startFrom={1308} volume={0.16} />
        </>
      )}

      {/* Intro (36 - 85) */}
      <Sequence from={36} durationInFrames={49}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <h1
            style={{
              color: "white",
              fontSize: 100,
              fontWeight: 950,
              transform: `scale(${introScale})`,
              textAlign: "center",
              textShadow: "0 10px 30px rgba(0,0,0,0.8)",
            }}
          >
            التحدي بيبدأ <span style={{ color: "#FFE600" }}>هلا</span>
          </h1>
        </AbsoluteFill>
      </Sequence>

      {/* Bookmark (85 - 124) */}
      <Sequence from={85} durationInFrames={39}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ transform: `scale(${bookmarkScale})`, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <span style={{ fontSize: 200, filter: "drop-shadow(0 0 40px rgba(255, 255, 255, 0.5))" }}>
              🔖
            </span>
            <h2 style={{ color: "white", fontSize: 60, marginTop: 20 }}>احفظ الفيديو</h2>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Laptop (124 - 151) */}
      <Sequence from={124} durationInFrames={27}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <span 
              style={{ 
                fontSize: 200, 
                transform: `scaleY(${laptopOpen})`,
                transformOrigin: "bottom",
                filter: "drop-shadow(0 0 50px rgba(0, 242, 254, 0.6))"
              }}
            >
              💻
            </span>
            <h2 style={{ color: "white", fontSize: 60, marginTop: 20 }}>افتح جهازك</h2>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Typing Code (151 - 225) */}
      <Sequence from={151} durationInFrames={74}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", backgroundColor: "#0F0F1A" }}>
          <div
            style={{
              background: "#1E1E2E",
              padding: "40px 60px",
              borderRadius: 20,
              border: "2px solid #313244",
              boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
              width: "80%",
            }}
          >
            <div style={{ display: "flex", gap: 10, marginBottom: 30 }}>
              <div style={{ width: 20, height: 20, borderRadius: 10, backgroundColor: "#F38BA8" }} />
              <div style={{ width: 20, height: 20, borderRadius: 10, backgroundColor: "#F9E2AF" }} />
              <div style={{ width: 20, height: 20, borderRadius: 10, backgroundColor: "#A6E3A1" }} />
            </div>
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 60, color: "#CDD6F4", margin: 0 }}>
              <span style={{ color: "#CBA6F7" }}>{displayedCode.startsWith("print") ? "print" : displayedCode}</span>
              {displayedCode.length > 5 && (
                <span style={{ color: "#89DCEB" }}>{displayedCode.substring(5, 6)}</span>
              )}
              {displayedCode.length > 6 && (
                <span style={{ color: "#A6E3A1" }}>{displayedCode.substring(6, Math.max(6, displayedCode.length - (displayedCode.endsWith(')') ? 1 : 0)))}</span>
              )}
              {displayedCode.endsWith(')') && (
                <span style={{ color: "#89DCEB" }}>)</span>
              )}
              <span style={{ opacity: frame % 10 < 5 ? 1 : 0, color: "#00F2FE", marginLeft: 5 }}>|</span>
            </p>
          </div>
          <h2 style={{ color: "white", fontSize: 50, position: "absolute", bottom: 200 }}>
            واكتب أول سطر كود
          </h2>
        </AbsoluteFill>
      </Sequence>

      {/* Finale: جاهز؟ (225 - 255) */}
      <Sequence from={225}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          {/* Deep dark vignette to focus all attention to the center without losing the cyber background */}
          <AbsoluteFill 
            style={{
              background: "radial-gradient(circle, transparent 0%, rgba(0,0,0,0.8) 100%)",
            }}
          />
          <h1
            style={{
              color: "#FFE600",
              fontSize: 250,
              fontWeight: 950,
              transform: `scale(${interpolate(finaleZoom, [0, 1], [3, 1])})`,
              margin: 0,
              display: "flex",
              alignItems: "center",
              textShadow: "0 0 80px rgba(255, 230, 0, 0.6), 0 0 20px rgba(255, 230, 0, 0.8)"
            }}
          >
            جاهز؟
            <span style={{ opacity: frame % 8 < 4 ? 1 : 0, color: "#00F2FE", marginLeft: 20, textShadow: "0 0 40px rgba(0, 242, 254, 0.8)" }}>_</span>
          </h1>
        </AbsoluteFill>
      </Sequence>

      {/* Fast SFX for cuts */}
      <Sequence from={85}>
        <Audio src={staticFile("media/sfx_pop.wav")} volume={0.8} />
      </Sequence>
      <Sequence from={124}>
        <Audio src={staticFile("media/sfx_swoosh.wav")} volume={0.7} />
      </Sequence>
      <Sequence from={151}>
        <Audio src={staticFile("media/sfx_keyboard.wav")} startFrom={0} endAt={74} volume={1} />
      </Sequence>
      <Sequence from={225}>
        <Audio src={staticFile("media/sfx_boom_impact.wav")} volume={1} />
      </Sequence>
      
    </AbsoluteFill>
  );
};
