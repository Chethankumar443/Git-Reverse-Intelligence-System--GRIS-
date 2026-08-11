'use client';
import React from 'react';

interface ThinkingOrbsProps {
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const ThinkingOrbs: React.FC<ThinkingOrbsProps> = ({ label = 'AI Synthesis Thinking…', size = 'md' }) => {
  const dimensions = {
    sm: { container: 48, orb1: 14, orb2: 18, orb3: 12 },
    md: { container: 72, orb1: 22, orb2: 28, orb3: 18 },
    lg: { container: 96, orb1: 30, orb2: 38, orb3: 24 },
  }[size];

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 12, userSelect: 'none' }}>
      <div
        style={{
          position: 'relative',
          width: dimensions.container,
          height: dimensions.container,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Orb 1: Cyan Ambient Core */}
        <div
          style={{
            position: 'absolute',
            width: dimensions.orb1,
            height: dimensions.orb1,
            borderRadius: '50%',
            background: 'radial-gradient(circle, #00dfd8 0%, rgba(0, 223, 216, 0.1) 70%)',
            boxShadow: '0 0 20px #00dfd8',
            filter: 'blur(2px)',
            animation: 'orb-float-1 3s ease-in-out infinite alternate',
          }}
        />

        {/* Orb 2: Violet Glowing Satellite */}
        <div
          style={{
            position: 'absolute',
            width: dimensions.orb2,
            height: dimensions.orb2,
            borderRadius: '50%',
            background: 'radial-gradient(circle, #7928ca 0%, rgba(121, 40, 202, 0.15) 75%)',
            boxShadow: '0 0 24px #7928ca',
            filter: 'blur(3px)',
            animation: 'orb-float-2 4s ease-in-out infinite alternate',
          }}
        />

        {/* Orb 3: Radiant White Pulsing Core */}
        <div
          style={{
            position: 'absolute',
            width: dimensions.orb3,
            height: dimensions.orb3,
            borderRadius: '50%',
            background: 'radial-gradient(circle, #ffffff 0%, rgba(0, 223, 216, 0.4) 60%, transparent 100%)',
            boxShadow: '0 0 16px rgba(255,255,255,0.8)',
            animation: 'orb-pulse 2s ease-in-out infinite',
          }}
        />
      </div>

      {label && (
        <span
          style={{
            fontSize: size === 'sm' ? 11 : 12,
            fontFamily: 'var(--font-mono)',
            fontWeight: 500,
            letterSpacing: '-0.01em',
            background: 'linear-gradient(135deg, #fafafa 0%, var(--color-cyan) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            animation: 'fade-pulse 1.8s ease-in-out infinite alternate',
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
};
