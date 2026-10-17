import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import NoteCard from "../components/NoteCard";
import ReviewForm from "../components/ReviewForm";
import { deleteNote, getNotes, getTypes, updateNote } from "../api/client";

export default function Notes() {
  const [notes, setNotes] = useState([]);
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter states
  const [selectedType, setSelectedType] = useState("");
  const [personFilter, setPersonFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Edit modal state
  const [editingNote, setEditingNote] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load types once
  useEffect(() => {
    getTypes()
      .then((data) => setTypes(data || []))
      .catch((err) => console.error("Failed to load types:", err));
  }, []);

  useEffect(() => {
    let ignore = false;
    const filters = {
      type_name: selectedType || null,
      person: personFilter.trim() || null,
      search: debouncedSearch.trim() || null,
    };
    getNotes(filters)
      .then((data) => {
        if (!ignore) setNotes(data || []);
      })
      .catch((err) => {
        if (!ignore) setError(err.message || "Failed to load notes.");
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [selectedType, personFilter, debouncedSearch, refreshCount]);

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this note?")) {
      return;
    }
    try {
      await deleteNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleEditConfirm = async (updatedNote) => {
    try {
      await updateNote(updatedNote.id, {
        summary: updatedNote.summary,
        status: updatedNote.status,
        fields: updatedNote.fields,
        missing_fields: updatedNote.missing_fields,
      });
      setEditingNote(null);
      setRefreshCount((c) => c + 1);
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    }
  };

  const handleClearFilters = () => {
    setSelectedType("");
    setPersonFilter("");
    setSearchQuery("");
  };

  const hasActiveFilters = Boolean(selectedType || personFilter || searchQuery);

  return (
    <div className="w-full min-h-[calc(100vh-4rem)] bg-[#080c18] text-white px-4 py-8">
      <div className="max-w-4xl mx-auto flex flex-col gap-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              Saved Notes
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Search, filter, and inspect your structured voice records.
            </p>
          </div>

          <Link
            to="/"
            className="self-start sm:self-auto px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition flex items-center gap-1.5"
          >
            <span>+</span> Record New Note
          </Link>
        </div>

        {/* Filter Bar */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between text-xs">
          <div className="flex-1 flex flex-col sm:flex-row gap-3">
            {/* Search input */}
            <div className="flex-1 relative">
              <input
                type="text"
                placeholder="Search transcript, summary, or fields..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-2 text-slate-400 hover:text-white"
                >
                  ✕
                </button>
              )}
            </div>

            {/* Type Filter */}
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
            >
              <option value="">All Types</option>
              {types.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name.toUpperCase()}
                </option>
              ))}
            </select>

            {/* Person Filter */}
            <input
              type="text"
              placeholder="Filter by person..."
              value={personFilter}
              onChange={(e) => setPersonFilter(e.target.value)}
              className="w-full sm:w-44 bg-slate-900 border border-white/10 rounded-xl px-3.5 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="text-indigo-400 hover:text-indigo-300 font-medium transition whitespace-nowrap cursor-pointer self-end md:self-center"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Notes Content */}
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-indigo-500/20 border-t-indigo-400 animate-spin" />
            <span className="text-xs text-slate-400">Loading notes...</span>
          </div>
        ) : error ? (
          <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs text-center">
            {error}
          </div>
        ) : notes.length === 0 ? (
          <div className="py-20 rounded-3xl bg-white/[0.02] border border-white/5 flex flex-col items-center justify-center text-center p-6 gap-3">
            <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 text-xl font-mono">
              📝
            </div>
            <h3 className="text-base font-bold text-white">No notes found</h3>
            <p className="text-xs text-slate-400 max-w-sm">
              {hasActiveFilters
                ? "No saved notes match your filters. Try clearing filters or searching for something else."
                : "You haven't saved any voice notes yet. Start recording your thoughts!"}
            </p>
            {hasActiveFilters ? (
              <button
                type="button"
                onClick={handleClearFilters}
                className="mt-2 text-xs text-indigo-400 hover:underline cursor-pointer"
              >
                Clear all filters
              </button>
            ) : (
              <Link
                to="/"
                className="mt-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
              >
                Record your first note
              </Link>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <span className="text-xs text-slate-400">
              Showing {notes.length} {notes.length === 1 ? "note" : "notes"}
            </span>
            {notes.map((note) => (
              <NoteCard
                key={note.id}
                note={note}
                onDelete={handleDelete}
                onEdit={(n) => setEditingNote(n)}
              />
            ))}
          </div>
        )}

        {/* Edit Note Modal */}
        {editingNote && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
            <div className="w-full max-w-xl my-8">
              <ReviewForm
                draft={editingNote}
                types={types}
                onConfirm={handleEditConfirm}
                onDiscard={() => setEditingNote(null)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
