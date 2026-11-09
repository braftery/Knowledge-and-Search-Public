import { Link, useParams } from "react-router-dom";
import { SpecimenFrame, specimens } from "@/gallery/specimens";

export function GalleryPage() {
  const { id } = useParams();
  if (id) {
    const specimen = specimens.find((item) => item.id === id);
    if (!specimen) {
      return (
        <main className="hh hh-pad">
          <h1 className="tools-title">That component is not in the gallery.</h1>
          <Link to="/gallery">Back to the gallery</Link>
        </main>
      );
    }
    return (
      <main>
        <SpecimenFrame specimen={specimen} />
      </main>
    );
  }

  return (
    <main className="hh" style={{ padding: "var(--space-8)", display: "flex", flexDirection: "column", gap: "var(--space-8)" }}>
      <header style={{ maxWidth: "var(--size-measure)" }}>
        <p className="tools-overline">Harbor Health</p>
        <h1 className="tools-title-lg">Component gallery</h1>
        <p className="tools-body">
          Each frame uses the design system tokens. Sample wording here is illustrative and matches the component previews.
        </p>
      </header>
      {specimens.map((specimen) => (
        <section key={specimen.id} aria-labelledby={`heading-${specimen.id}`}>
          <h2 id={`heading-${specimen.id}`} className="tools-title-sm" style={{ marginBottom: "var(--space-3)" }}>
            {specimen.title}
          </h2>
          <SpecimenFrame specimen={specimen} />
        </section>
      ))}
    </main>
  );
}
