import { Mic, NotebookPen } from "lucide-react";
import { Link, NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Record", icon: Mic, end: true },
  { to: "/notes", label: "Notes", icon: NotebookPen, end: false },
];

export default function NavBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/6 bg-ink-950/75 backdrop-blur-lg">
      <div className="flex h-14 items-center justify-between px-4 sm:h-16 sm:px-6">
        <Link
          to="/"
          className="flex items-center gap-2.5 rounded-lg outline-none focus-visible:ring-4 focus-visible:ring-accent/30"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-ink-950 shadow-md shadow-black/40">
            <Mic size={16} strokeWidth={2.5} aria-hidden="true" />
          </span>
          <span className="font-display text-xl font-semibold tracking-tight text-white">YapIt</span>
        </Link>

        <nav aria-label="Main" className="flex items-center gap-1 rounded-full border border-white/7 bg-white/3 p-1">
          {LINKS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium transition outline-none focus-visible:ring-4 focus-visible:ring-accent/30 ${
                  isActive ? "bg-white text-ink-950 shadow" : "text-slate-400 hover:text-white"
                }`
              }
            >
              <Icon size={15} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
