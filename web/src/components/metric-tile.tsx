type MetricTileProps = {
  label: string;
  value: string;
  context: string;
  href?: string;
  linkLabel?: string;
};

export function MetricTile({ label, value, context, href, linkLabel }: MetricTileProps) {
  return (
    <div className="hh-metric">
      <div className="hh-metric__label">{label}</div>
      <div className="hh-metric__value">{value}</div>
      <div className="hh-meta">{context}</div>
      {href && linkLabel ? (
        <a className="hh-btn hh-btn--tertiary hh-btn--compact" href={href} style={{ marginTop: 8, alignSelf: "flex-start" }}>
          {linkLabel}
        </a>
      ) : null}
    </div>
  );
}
