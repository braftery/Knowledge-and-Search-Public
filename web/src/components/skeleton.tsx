type SkeletonProps = {
  width?: string;
  height?: string;
  label?: string;
};

export function Skeleton({ width, height, label = "Loading" }: SkeletonProps) {
  return <div className="hh-skel" style={{ width, height }} aria-hidden="true" data-label={label} />;
}

export function AnswerSkeleton() {
  return (
    <div className="hh-answer" style={{ maxWidth: 400 }} aria-busy="true" aria-label="Loading answers">
      <div className="hh-skel" style={{ width: "60%" }} />
      <div className="hh-skel" style={{ height: 72 }} />
      <div className="hh-skel" style={{ width: "80%" }} />
    </div>
  );
}
