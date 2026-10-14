'use client';

import React from 'react';

const VIDEO_SRC = '/ui/auth/login-bg.mp4';
const POSTER_SRC = '/ui/portal/simulation-hero.png';

export const AuthVideoBackground: React.FC = () => (
  <div className="ui-auth-video ui-auth-video--enter" aria-hidden>
    <video
      className="ui-auth-video__media"
      autoPlay
      muted
      loop
      playsInline
      preload="metadata"
      poster={POSTER_SRC}
    >
      <source src={VIDEO_SRC} type="video/mp4" />
    </video>
    <div className="ui-auth-video__overlay" />
  </div>
);
