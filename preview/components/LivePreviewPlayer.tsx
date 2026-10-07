/**
 * preview/components/LivePreviewPlayer.tsx — React UI Wrapper for Live Preview Runtime.
 * S28-R06: Lightweight React player UI shell around pure BrowserPreviewRuntime.
 * Invariant: ZERO canonical semantics or timeline math inside React.
 */
import React, { useEffect, useRef, useState } from "react";
import { BrowserPreviewRuntime } from "../preview-runtime";
import type { BlueprintV2 } from "../../contracts/blueprint";
import type { NormalizedVideo } from "../../contracts/normalization";

export interface LivePreviewPlayerProps {
  runtime?: BrowserPreviewRuntime;
  document?: BlueprintV2 | NormalizedVideo | any;
  width?: number | string;
  height?: number | string;
  showControls?: boolean;
  className?: string;
}

export const LivePreviewPlayer: React.FC<LivePreviewPlayerProps> = ({
  runtime: propRuntime,
  document: propDocument,
  width = "100%",
  height = "540px",
  showControls = true,
  className = "",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<BrowserPreviewRuntime | null>(propRuntime ?? null);

  const [currentFrame, setCurrentFrame] = useState<number>(0);
  const [durationFrames, setDurationFrames] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [fps, setFps] = useState<number>(30);
  const [timeMs, setTimeMs] = useState<number>(0);

  // Initialize or synchronize runtime
  useEffect(() => {
    let runtime = runtimeRef.current;
    let createdInternally = false;

    if (!runtime && propDocument) {
      runtime = new BrowserPreviewRuntime(propDocument);
      runtimeRef.current = runtime;
      createdInternally = true;
    }

    if (!runtime) return;

    if (propDocument && !createdInternally) {
      runtime.updateDocument(propDocument);
    }

    if (containerRef.current) {
      runtime.mount(containerRef.current);
    }

    // Synchronize initial state
    setCurrentFrame(runtime.getCurrentFrame());
    setDurationFrames(runtime.getDurationFrames());
    setIsPlaying(runtime.getState() === "playing");
    setFps(runtime.getFps());
    setTimeMs(runtime.getCurrentTimeMs());

    // Bind event listeners
    const unsubFrame = runtime.on("frame", (f, ms) => {
      setCurrentFrame(f);
      setTimeMs(ms);
    });

    const unsubPlay = runtime.on("play", () => setIsPlaying(true));
    const unsubPause = runtime.on("pause", () => setIsPlaying(false));
    const unsubSeek = runtime.on("seek", (f) => setCurrentFrame(f));

    return () => {
      unsubFrame();
      unsubPlay();
      unsubPause();
      unsubSeek();
      if (createdInternally) {
        runtime?.destroy();
        runtimeRef.current = null;
      }
    };
  }, [propDocument, propRuntime]);

  const handleTogglePlay = () => {
    const rt = runtimeRef.current;
    if (!rt) return;
    if (isPlaying) {
      rt.pause();
    } else {
      rt.play();
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const target = Number(e.target.value);
    runtimeRef.current?.seek(target);
  };

  const handleStepBack = () => {
    runtimeRef.current?.stepBackward(1);
  };

  const handleStepForward = () => {
    runtimeRef.current?.stepForward(1);
  };

  const formatTimecode = (ms: number) => {
    const totalSec = Math.floor(ms / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    const remMs = Math.floor(ms % 1000);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(remMs).padStart(3, "0")}`;
  };

  return (
    <div
      className={`cv-live-preview-player ${className}`}
      style={{
        display: "flex",
        flexDirection: "column",
        width,
        height,
        backgroundColor: "#050811",
        borderRadius: "8px",
        overflow: "hidden",
        boxShadow: "0 4px 20px rgba(0,0,0,0.6)",
      }}
    >
      {/* Visual Canvas Stage Container */}
      <div
        ref={containerRef}
        className="cv-stage-viewport"
        style={{
          flex: 1,
          width: "100%",
          minHeight: 0,
          position: "relative",
        }}
      />

      {/* Interactive Controls Bar */}
      {showControls && (
        <div
          className="cv-controls-bar"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "10px 16px",
            backgroundColor: "#0d1322",
            borderTop: "1px solid #1e293b",
            color: "#e2e8f0",
            fontSize: "13px",
            fontFamily: "system-ui, -apple-system, sans-serif",
            userSelect: "none",
          }}
        >
          {/* Step Backward Button */}
          <button
            onClick={handleStepBack}
            title="Step backward 1 frame"
            style={{
              background: "transparent",
              border: "1px solid #334155",
              color: "#94a3b8",
              borderRadius: "4px",
              padding: "4px 8px",
              cursor: "pointer",
            }}
          >
            -1f
          </button>

          {/* Play / Pause Button */}
          <button
            onClick={handleTogglePlay}
            style={{
              backgroundColor: isPlaying ? "#f59e0b" : "#3b82f6",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "4px",
              padding: "6px 14px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isPlaying ? "Pause" : "Play"}
          </button>

          {/* Step Forward Button */}
          <button
            onClick={handleStepForward}
            title="Step forward 1 frame"
            style={{
              background: "transparent",
              border: "1px solid #334155",
              color: "#94a3b8",
              borderRadius: "4px",
              padding: "4px 8px",
              cursor: "pointer",
            }}
          >
            +1f
          </button>

          {/* Timecode / Frame display */}
          <span style={{ fontFamily: "monospace", color: "#38bdf8" }}>
            F: {currentFrame} / {Math.max(0, durationFrames - 1)}
          </span>
          <span style={{ fontFamily: "monospace", color: "#64748b" }}>
            ({formatTimecode(timeMs)})
          </span>

          {/* Scrubber slider */}
          <input
            type="range"
            min={0}
            max={Math.max(0, durationFrames - 1)}
            value={currentFrame}
            onChange={handleSeek}
            style={{
              flex: 1,
              cursor: "pointer",
              accentColor: "#3b82f6",
            }}
          />

          {/* FPS Badge */}
          <span
            style={{
              fontSize: "11px",
              backgroundColor: "#1e293b",
              padding: "2px 6px",
              borderRadius: "4px",
              color: "#94a3b8",
            }}
          >
            {fps} FPS
          </span>
        </div>
      )}
    </div>
  );
};
