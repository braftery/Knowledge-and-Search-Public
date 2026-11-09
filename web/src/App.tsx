import { Link, Route, Routes } from "react-router-dom";
import { GalleryPage } from "@/gallery/GalleryPage";
import { AppToaster } from "@/components/toast";
import { DemoPage } from "@/pages/demo/DemoPage";
import { ExploreLayout } from "@/pages/ExploreLayout";
import { LauncherPage } from "@/pages/LauncherPage";
import { PilotPage } from "@/pages/PilotPage";
import { EvalsPage } from "@/pages/EvalsPage";

export function App() {
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <Routes>
        <Route path="/" element={<LauncherPage />} />
        <Route path="/gallery" element={<GalleryPage />} />
        <Route path="/gallery/:id" element={<GalleryPage />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/pilot" element={<PilotPage />} />
        <Route path="/evals" element={<EvalsPage />} />
        <Route path="/explore/:roleId" element={<ExploreLayout />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <AppToaster />
    </>
  );
}

function NotFound() {
  return (
    <main id="main-content" className="hh hh-pad" data-theme="tools" style={{ maxWidth: "var(--size-measure)" }}>
      <h1 className="tools-title">That page is not in the prototype</h1>
      <p className="tools-body">The address does not match a Harbor Health surface.</p>
      <p>
        <Link to="/">Back to the launcher</Link>
      </p>
    </main>
  );
}
