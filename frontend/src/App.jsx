import { BrowserRouter, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import Home from "./pages/Home";
import Notes from "./pages/Notes";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-dvh flex-col">
        <NavBar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/notes" element={<Notes />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
