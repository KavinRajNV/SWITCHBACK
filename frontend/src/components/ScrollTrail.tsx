import React, { useState, useEffect } from 'react';
import { motion, useScroll, useSpring, useTransform } from 'framer-motion';

import run1 from '../assets/run_1.webp';
import run2 from '../assets/run_2.webp';
import run3 from '../assets/run_3.webp';
import run4 from '../assets/run_4.webp';
import run5 from '../assets/run_5.webp';

const RUNNER_SPRITES = [run1, run2, run3, run4, run5];

export const ScrollTrail: React.FC = () => {
  const { scrollYProgress } = useScroll();
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 100, damping: 30, restDelta: 0.001 });

  // Frame index 0..4 based on scroll percentage
  const spriteIndex = useTransform(smoothProgress, [0, 1], [0, RUNNER_SPRITES.length * 8]);
  const [currFrame, setCurrFrame] = useState(0);

  useEffect(() => {
    const unsubscribe = spriteIndex.on('change', (latest) => {
      setCurrFrame(Math.floor(latest) % RUNNER_SPRITES.length);
    });
    return () => unsubscribe();
  }, [spriteIndex]);

  // Runner vertical Y position following scroll path
  const runnerYPercent = useTransform(smoothProgress, [0, 1], ['5%', '92%']);

  return (
    <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-full max-w-7xl pointer-events-none z-20 hidden md:block">
      {/* SVG Winding Trail Line */}
      <svg
        className="w-full h-full overflow-visible"
        viewBox="0 0 1200 2400"
        fill="none"
        preserveAspectRatio="none"
      >
        {/* Background Guide Path */}
        <path
          d="M 600 100 C 900 400, 1000 700, 600 1000 C 200 1300, 300 1700, 600 2200"
          stroke="#E4DFD3"
          strokeWidth="4"
          strokeDasharray="8 8"
        />

        {/* Animated Trail Line */}
        <motion.path
          d="M 600 100 C 900 400, 1000 700, 600 1000 C 200 1300, 300 1700, 600 2200"
          stroke="#E08A34"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray="12 8"
          style={{
            pathLength: smoothProgress,
          }}
        />
      </svg>

      {/* Runner Sprite Marker at Leading Head of Trail */}
      <motion.div
        className="absolute left-1/2 -translate-x-1/2 w-14 h-14 flex items-center justify-center transition-all duration-75"
        style={{ top: runnerYPercent }}
      >
        <div className="relative">
          <img
            src={RUNNER_SPRITES[currFrame]}
            alt="Runner Sprite"
            className="w-12 h-12 object-contain drop-shadow-md"
          />
          {/* Glowing Trail Pin */}
          <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-amber rounded-full animate-ping opacity-75" />
        </div>
      </motion.div>
    </div>
  );
};
