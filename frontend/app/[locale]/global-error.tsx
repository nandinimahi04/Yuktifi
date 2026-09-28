"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("YuktiFi Global Error:", error);
  }, [error]);

  return (
    <html>
      <body>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', padding: '20px' }}>
          <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: '#e11d48' }}>Fatal Application Error</h2>
          <pre style={{ background: '#f1f5f9', padding: '16px', borderRadius: '8px', maxWidth: '800px', overflowX: 'auto', marginTop: '16px', color: '#334155' }}>
            {error.message || "Unknown global error"}
          </pre>
          <button 
            onClick={() => reset()}
            style={{ marginTop: '24px', padding: '10px 20px', background: '#4f46e5', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
