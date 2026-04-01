import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { useDarkMode } from "./hooks/useDarkMode";
import "./App.css";

function Placeholder({ name }: { name: string }) {
  return <div className="loading">{name} page — coming soon</div>;
}

export default function App() {
  const { dark, toggle } = useDarkMode();

  return (
    <BrowserRouter basename="/papercrawl">
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
          <Route path="/" element={<Placeholder name="Home" />} />
          <Route
            path="/conference/:id"
            element={<Placeholder name="Conference" />}
          />
          <Route path="/author/:name" element={<Placeholder name="Author" />} />
          <Route path="/trends" element={<Placeholder name="Trends" />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
