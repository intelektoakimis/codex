'use client';

import { useMemo, useState } from 'react';

const MESSAGES = [
  { x: 60, y: -40 },
  { x: -80, y: 50 },
  { x: 95, y: 30 },
  { x: -70, y: -55 },
  { x: 0, y: 70 },
  { x: 110, y: -10 }
];

export default function Home() {
  const [accepted, setAccepted] = useState(false);
  const [dodgeIndex, setDodgeIndex] = useState(0);

  const dodgePosition = useMemo(() => MESSAGES[dodgeIndex % MESSAGES.length], [dodgeIndex]);

  const moveNoButton = () => {
    setDodgeIndex((prev) => prev + 1);
  };

  return (
    <main className="page">
      <div className="floating-hearts" aria-hidden="true">
        <span>💖</span>
        <span>💕</span>
        <span>💘</span>
      </div>

      <section className="card">
        <h1>Will you be my Valentine? 🌹</h1>
        <p>
          I promise cute vibes, sweet laughs, and a magical night. What do you say?
        </p>

        {!accepted ? (
          <div className="button-zone">
            <button className="yes" onClick={() => setAccepted(true)}>
              Yes 💞
            </button>
            <button
              className="no"
              onMouseEnter={moveNoButton}
              onClick={moveNoButton}
              style={{
                transform: `translate(${dodgePosition.x}px, ${dodgePosition.y}px)`
              }}
            >
              No 🙈
            </button>
          </div>
        ) : (
          <div className="love-note" role="status" aria-live="polite">
            Yay! You said yes! 🥰
            <br />
            We are going out for dinner on <strong>February 14th</strong> — be ready for a
            romantic evening! ✨🍽️
          </div>
        )}
      </section>
    </main>
  );
}
