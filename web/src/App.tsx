import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { useDarkMode } from "./hooks/useDarkMode";
import { useManifest } from "./hooks/useManifest";
import { Home } from "./pages/Home";
import { Conference } from "./pages/Conference";
import { Author } from "./pages/Author";
import { Trends } from "./pages/Trends";
import "./App.css";

export default function App() {
  const { dark, toggle } = useDarkMode();
  const { citationUpdated } = useManifest();

  return (
    <BrowserRouter basename="/paper-explorer">
      <div className="app-layout">
        <header className="app-header">
          <h1>
            <NavLink to="/" style={{ color: "inherit" }}>
              Paper Explorer
            </NavLink>
          </h1>
          <nav>
            <NavLink to="/">Conferences</NavLink>
            <NavLink to="/trends">Trends</NavLink>
            <button className="theme-toggle" onClick={toggle}>
              {dark ? "☀" : "☾"}
            </button>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/conference/:id" element={<Conference />} />
          <Route path="/author/:name" element={<Author />} />
          <Route path="/trends" element={<Trends />} />
        </Routes>
        <footer className="app-footer">
          {citationUpdated && (
            <div className="citation-updated">Citation data last updated: {citationUpdated}</div>
          )}
          Made with ♥ by <a href="https://brightjade.github.io/" target="_blank" rel="noopener noreferrer">Minseok Choi</a>
        </footer>
      </div>
    </BrowserRouter>
  );
}
