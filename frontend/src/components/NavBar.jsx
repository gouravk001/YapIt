import { Link, useLocation } from "react-router-dom";

export default function NavBar() {
  const location = useLocation();

  const isHome = location.pathname === "/";
  const isNotes = location.pathname.startsWith("/notes");

  return (
    <header className="w-full bg-[#080c18]/80 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-sm shadow-md group-hover:scale-105 transition-transform">
            Y
          </div>
          <span className="text-xl font-bold tracking-tight text-white group-hover:text-indigo-300 transition-colors">
            YapIt
          </span>
          <span className="text-[10px] font-semibold uppercase tracking-widest text-indigo-400 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded-full ml-1">
            Local
          </span>
        </Link>

        {/* Navigation links */}
        <nav className="flex items-center gap-1 sm:gap-2">
          <Link
            to="/"
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
              isHome
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            Record
          </Link>

          <Link
            to="/notes"
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
              isNotes
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            Saved Notes
          </Link>
        </nav>
      </div>
    </header>
  );
}

