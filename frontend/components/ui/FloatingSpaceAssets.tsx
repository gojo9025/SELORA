"use client";

import React from "react";
import { motion } from "framer-motion";
import { Satellite, Rocket, Globe, Moon, Telescope, Asterisk } from "lucide-react";

const ASSETS = [
  { id: 1, Icon: Satellite, size: 48, top: "10%", left: "5%", delay: 0, duration: 15, rotate: 15 },
  { id: 2, Icon: Rocket, size: 64, top: "60%", left: "85%", delay: 2, duration: 12, rotate: -45 },
  { id: 3, Icon: Globe, size: 120, top: "80%", left: "10%", delay: 1, duration: 25, rotate: 0 },
  { id: 4, Icon: Moon, size: 40, top: "20%", left: "80%", delay: 3, duration: 18, rotate: -20 },
  { id: 5, Icon: Telescope, size: 52, top: "40%", left: "90%", delay: 4, duration: 20, rotate: 10 },
  { id: 6, Icon: Asterisk, size: 24, top: "30%", left: "20%", delay: 1, duration: 8, rotate: 180 },
  { id: 7, Icon: Asterisk, size: 16, top: "70%", left: "70%", delay: 3, duration: 10, rotate: -180 },
];

export default function FloatingSpaceAssets() {
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: 0,
        opacity: 0.15, // Subtle background effect
      }}
    >
      {ASSETS.map(({ id, Icon, size, top, left, delay, duration, rotate }) => (
        <motion.div
          key={id}
          style={{
            position: "absolute",
            top,
            left,
            color: "var(--accent-cyan)", // Match the branding color
          }}
          initial={{ y: 0, rotate }}
          animate={{
            y: ["0%", "-20%", "0%"],
            rotate: [rotate, rotate + 5, rotate - 5, rotate],
          }}
          transition={{
            y: {
              duration: duration,
              repeat: Infinity,
              ease: "easeInOut",
              delay: delay,
            },
            rotate: {
              duration: duration * 1.5,
              repeat: Infinity,
              ease: "easeInOut",
              delay: delay,
            }
          }}
        >
          <Icon size={size} strokeWidth={1} />
        </motion.div>
      ))}
      
      {/* Decorative gradient orb */}
      <div
        style={{
          position: "absolute",
          top: "40%",
          left: "50%",
          width: "60vw",
          height: "60vw",
          transform: "translate(-50%, -50%)",
          background: "radial-gradient(circle, rgba(0,200,255,0.03) 0%, rgba(0,0,0,0) 70%)",
          zIndex: -1,
        }}
      />
    </div>
  );
}
