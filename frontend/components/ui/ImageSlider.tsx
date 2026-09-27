"use client";

import React, { useState, useRef, useEffect, MouseEvent as ReactMouseEvent, TouchEvent as ReactTouchEvent } from "react";
import { MoveHorizontal } from "lucide-react";

interface ImageSliderProps {
  sourceImage: string;
  referenceImage: string;
  sourceLabel?: string;
  referenceLabel?: string;
  width?: string | number;
  height?: string | number;
}

export default function ImageSlider({
  sourceImage,
  referenceImage,
  sourceLabel = "Warped Source",
  referenceLabel = "Reference",
  width = "100%",
  height = 500,
}: ImageSliderProps) {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMove = (clientX: number) => {
    if (!isDragging || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    const percent = Math.max(0, Math.min((x / rect.width) * 100, 100));
    setSliderPosition(percent);
  };

  const handleMouseMove = (e: MouseEvent) => {
    handleMove(e.clientX);
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (e.touches.length > 0) {
      handleMove(e.touches[0].clientX);
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
      window.addEventListener("touchmove", handleTouchMove, { passive: false });
      window.addEventListener("touchend", handleMouseUp);
    } else {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleMouseUp);
    };
  }, [isDragging]);

  const handleMouseDown = (e: ReactMouseEvent) => {
    setIsDragging(true);
    handleMove(e.clientX);
  };

  const handleTouchStart = (e: ReactTouchEvent) => {
    setIsDragging(true);
    handleMove(e.touches[0].clientX);
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: "relative",
        width,
        height,
        overflow: "hidden",
        borderRadius: "var(--radius-lg)",
        backgroundColor: "var(--bg-card)",
        cursor: isDragging ? "grabbing" : "crosshair",
        userSelect: "none",
        touchAction: "none",
        border: "1px solid var(--border)",
      }}
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
    >
      {/* Background: Reference Image */}
      <img
        src={referenceImage}
        alt="Reference"
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          objectFit: "contain",
          pointerEvents: "none",
        }}
        draggable={false}
      />
      <div
        style={{
          position: "absolute",
          top: 16,
          right: 16,
          background: "rgba(0,0,0,0.6)",
          padding: "4px 10px",
          borderRadius: 4,
          fontSize: 12,
          color: "white",
          pointerEvents: "none",
        }}
      >
        {referenceLabel}
      </div>

      {/* Foreground: Source Image (Clipped) */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          clipPath: `inset(0 ${100 - sliderPosition}% 0 0)`,
          pointerEvents: "none",
        }}
      >
        <img
          src={sourceImage}
          alt="Source"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "contain",
          }}
          draggable={false}
        />
        <div
          style={{
            position: "absolute",
            top: 16,
            left: 16,
            background: "rgba(0,200,255,0.7)",
            padding: "4px 10px",
            borderRadius: 4,
            fontSize: 12,
            color: "white",
            pointerEvents: "none",
            boxShadow: "0 0 10px rgba(0, 200, 255, 0.4)",
          }}
        >
          {sourceLabel}
        </div>
      </div>

      {/* Slider Handle */}
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: `${sliderPosition}%`,
          width: 2,
          backgroundColor: "#fff",
          transform: "translateX(-50%)",
          pointerEvents: "none",
          boxShadow: "0 0 10px rgba(0,0,0,0.5)",
          zIndex: 10,
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 32,
            height: 32,
            backgroundColor: "#fff",
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            color: "#333",
          }}
        >
          <MoveHorizontal size={18} />
        </div>
      </div>
    </div>
  );
}
