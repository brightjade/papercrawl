import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

function Placeholder({ name }: { name: string }) {
  return <div style={{ padding: "2rem" }}>{name} page — coming soon</div>;
}

export default function App() {
  return (
    <BrowserRouter basename="/papercrawl">
      <nav style={{ padding: "1rem", borderBottom: "1px solid #ccc" }}>
        <Link to="/">Home</Link> | <Link to="/trends">Trends</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Placeholder name="Home" />} />
        <Route path="/conference/:id" element={<Placeholder name="Conference" />} />
        <Route path="/author/:name" element={<Placeholder name="Author" />} />
        <Route path="/trends" element={<Placeholder name="Trends" />} />
      </Routes>
    </BrowserRouter>
  );
}
