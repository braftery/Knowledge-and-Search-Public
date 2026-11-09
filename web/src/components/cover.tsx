export function Cover() {
  return (
    <div className="cover" style={{ position: "relative", height: 288, overflow: "hidden", background: "var(--surface)" }}>
      <div aria-hidden="true" style={{ position: "absolute", top: 0, left: 480, width: 480, height: 288, overflow: "hidden" }}>
        <svg viewBox="0 0 480 288" width="480" height="288">
          <rect fill="var(--action)" x="16" y="-16" width="112" height="152" rx="6" />
          <g data-theme="member">
            <rect fill="var(--action)" x="16" y="152" width="112" height="56" rx="6" />
            <rect fill="var(--surface-sunken)" x="16" y="224" width="112" height="40" rx="6" />
          </g>
          <rect fill="var(--surface-inverse)" x="144" y="32" width="352" height="232" rx="6" />
          <rect fill="var(--approved)" x="160" y="48" width="48" height="16" rx="4" />
          <g data-theme="member">
            <g fill="var(--surface-sunken)">
              <path d="M168 248a12 12 0 0 1 24 0Z" />
              <path d="M200 248a12 12 0 0 1 24 0Z" />
              <path d="M264 248a12 12 0 0 1 24 0Z" />
              <path d="M296 248a12 12 0 0 1 24 0Z" />
              <path d="M360 248a12 12 0 0 1 24 0Z" />
              <path d="M392 248a12 12 0 0 1 24 0Z" />
              <path d="M424 248a12 12 0 0 1 24 0Z" />
              <path d="M184 216a12 12 0 0 1 24 0Z" />
              <path d="M312 216a12 12 0 0 1 24 0Z" />
              <path d="M376 216a12 12 0 0 1 24 0Z" />
              <path d="M216 184a12 12 0 0 1 24 0Z" />
              <path d="M344 184a12 12 0 0 1 24 0Z" />
            </g>
            <g fill="var(--action)">
              <path d="M232 248a12 12 0 0 1 24 0Z" />
              <path d="M328 248a12 12 0 0 1 24 0Z" />
              <path d="M248 216a12 12 0 0 1 24 0Z" />
              <path d="M408 216a12 12 0 0 1 24 0Z" />
              <path d="M280 152a12 12 0 0 1 24 0Z" />
            </g>
          </g>
        </svg>
      </div>
      <div style={{ position: "absolute", left: "var(--space-8)", bottom: "var(--space-6)", maxWidth: 440 }}>
        <h1
          style={{
            margin: 0,
            fontFamily: "var(--font-serif)",
            fontSize: 100,
            lineHeight: 0.95,
            fontWeight: 600,
            letterSpacing: "-0.01em",
            color: "var(--ink)",
          }}
        >
          Harbor
          <br />
          Health
        </h1>
        <p style={{ margin: "var(--space-3) 0 0 4px", fontSize: 16, lineHeight: "24px", color: "var(--ink-muted)" }}>
          One approved answer, in every channel. Fictional brand, illustrative data.
        </p>
      </div>
    </div>
  );
}
