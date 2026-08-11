import React from 'react';
import { motion } from 'framer-motion';

interface RevealProps {
  children: React.ReactNode;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right';
  className?: string;
}

export const Reveal: React.FC<RevealProps> = ({
  children,
  delay = 0,
  direction = 'up',
  className = '',
}) => {
  const getVariants = () => {
    switch (direction) {
      case 'up':
        return {
          hidden: { opacity: 0, y: 24, clipPath: 'inset(100% 0% 0% 0%)' },
          visible: { opacity: 1, y: 0, clipPath: 'inset(0% 0% 0% 0%)' },
        };
      case 'down':
        return {
          hidden: { opacity: 0, y: -24, clipPath: 'inset(0% 0% 100% 0%)' },
          visible: { opacity: 1, y: 0, clipPath: 'inset(0% 0% 0% 0%)' },
        };
      case 'left':
        return {
          hidden: { opacity: 0, x: 24, clipPath: 'inset(0% 0% 0% 100%)' },
          visible: { opacity: 1, x: 0, clipPath: 'inset(0% 0% 0% 0%)' },
        };
      case 'right':
        return {
          hidden: { opacity: 0, x: -24, clipPath: 'inset(0% 100% 0% 0%)' },
          visible: { opacity: 1, x: 0, clipPath: 'inset(0% 0% 0% 0%)' },
        };
    }
  };

  return (
    <motion.div
      variants={getVariants()}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-40px' }}
      transition={{
        duration: 0.6,
        delay,
        ease: [0.16, 1, 0.3, 1], // Geist spring easing
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
};
