export type RankRow = {
  label: string;
  detail?: string;
  count: number;
  href?: string;
};

type RankedBarsProps = {
  rows: RankRow[];
  maxVisible?: number;
  moreHref?: string;
  moreLabel?: string;
};

export function RankedBars({ rows, maxVisible = 6, moreHref, moreLabel = "See the full list" }: RankedBarsProps) {
  const sorted = [...rows].sort((a, b) => b.count - a.count);
  const visible = sorted.slice(0, maxVisible);
  const top = visible[0]?.count || 1;
  const hidden = sorted.length - visible.length;

  return (
    <div>
      {visible.map((row) => {
        const width = Math.max(4, Math.round((100 * row.count) / top));
        return (
          <div className="hh-rank" key={`${row.label}-${row.detail ?? ""}`}>
            <div>
              {row.href ? <a href={row.href}>{row.label}</a> : row.label}
              {row.detail ? <div className="hh-meta">{row.detail}</div> : null}
            </div>
            <div className="hh-rank__track" aria-hidden="true">
              <div className="hh-rank__bar" style={{ width: `${width}%` }} />
            </div>
            <div className="hh-rank__n">{row.count}</div>
          </div>
        );
      })}
      {hidden > 0 && moreHref ? (
        <a className="hh-btn hh-btn--tertiary" href={moreHref}>
          {moreLabel}
        </a>
      ) : null}
    </div>
  );
}
