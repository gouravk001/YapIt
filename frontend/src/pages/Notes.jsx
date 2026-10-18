import { Inbox, LoaderCircle, Mic, SearchX } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteNote, getNotes, getTypes, updateNote } from "../api/client";
import Banner from "../components/Banner";
import Dialog from "../components/Dialog";
import NoteCard from "../components/NoteCard";
import NotesFilterBar from "../components/NotesFilterBar";
import ReviewForm from "../components/ReviewForm";
import UndoToast from "../components/UndoToast";
import { UNDO_SECONDS } from "../config";
import { usePendingDelete } from "../hooks/usePendingDelete";
import { groupByDay } from "../lib/format";

const EMPTY_FILTERS = { search: "", person: "", type: "" };
const SEARCH_DEBOUNCE_MS = 300;

function useDebounced(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function EmptyState({ filtered, onClear }) {
  const Icon = filtered ? SearchX : Inbox;
  return (
    <div className="surface flex animate-fade-in flex-col items-center gap-3 px-6 py-16 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white/5 text-slate-400">
        <Icon size={22} aria-hidden="true" />
      </span>
      <h2 className="font-display text-xl font-semibold text-white">
        {filtered ? "Nothing matches" : "No notes yet"}
      </h2>
      <p className="max-w-xs text-sm text-slate-400">
        {filtered
          ? "Try a different search, or clear the filters to see everything."
          : "Record your first note and it will show up here."}
      </p>
      {filtered ? (
        <button type="button" onClick={onClear} className="btn-subtle mt-1">
          Clear filters
        </button>
      ) : (
        <Link to="/" className="btn-primary mt-1">
          <Mic size={16} aria-hidden="true" />
          Record a note
        </Link>
      )}
    </div>
  );
}

export default function Notes() {
  const [notes, setNotes] = useState([]);
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [editingNote, setEditingNote] = useState(null);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [refreshCount, setRefreshCount] = useState(0);

  const search = useDebounced(filters.search.trim(), SEARCH_DEBOUNCE_MS);
  const person = useDebounced(filters.person.trim(), SEARCH_DEBOUNCE_MS);
  const hasFilters = Boolean(filters.search || filters.person || filters.type);
  const typeByName = Object.fromEntries(types.map((t) => [t.name, t]));

  useEffect(() => {
    getTypes()
      .then((data) => setTypes(data || []))
      .catch(() => setTypes([]));
  }, []);

  useEffect(() => {
    let ignore = false;
    getNotes({ type_name: filters.type || null, person: person || null, search: search || null })
      .then((data) => {
        if (ignore) return;
        setNotes(data || []);
        setError(null);
      })
      .catch((err) => !ignore && setError(err.message || "Couldn't load your notes."))
      .finally(() => !ignore && setLoading(false));
    return () => {
      ignore = true;
    };
  }, [filters.type, person, search, refreshCount]);

  const commitDelete = async (id) => {
    try {
      await deleteNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      setError(`Couldn't delete the note: ${err.message}`);
    }
  };
  const pendingDelete = usePendingDelete(commitDelete, UNDO_SECONDS * 1000);
  const visibleNotes = notes.filter((n) => n.id !== pendingDelete.pendingId);

  const handleEditSave = async (note) => {
    setIsSavingEdit(true);
    try {
      await updateNote(note.id, {
        summary: note.summary,
        status: note.status,
        fields: note.fields,
        missing_fields: note.missing_fields,
      });
      setEditingNote(null);
      setRefreshCount((c) => c + 1);
    } catch (err) {
      setError(`Couldn't save your changes: ${err.message}`);
    } finally {
      setIsSavingEdit(false);
    }
  };

  return (
    // Fixed-height column: the header and filters stay put, only the list below them scrolls.
    <div className="mx-auto flex h-[calc(100dvh-3.5rem)] w-full max-w-3xl flex-col px-4 pt-8 sm:h-[calc(100dvh-4rem)] sm:pt-12">
      <div className="shrink-0">
        <header className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">Notes</h1>
            <p className="mt-1 text-sm text-slate-400">
              {loading
                ? "Loading…"
                : `${visibleNotes.length} ${visibleNotes.length === 1 ? "note" : "notes"}${hasFilters ? " found" : ""}`}
            </p>
          </div>
          <Link to="/" className="btn-primary">
            <Mic size={16} aria-hidden="true" />
            <span className="hidden sm:inline">New note</span>
            <span className="sr-only sm:hidden">New note</span>
          </Link>
        </header>

        <NotesFilterBar types={types} filters={filters} onChange={setFilters} />

        {error && (
          <div className="mt-6">
            <Banner>{error}</Banner>
          </div>
        )}
      </div>

      <div
        aria-label="Notes list"
        className="-mx-4 mt-3 min-h-0 flex-1 overflow-y-auto px-4 pt-3 pb-8 [mask-image:linear-gradient(to_bottom,transparent,black_1rem)]"
      >
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-20 text-sm text-slate-400">
            <LoaderCircle size={18} className="animate-spin" aria-hidden="true" />
            Loading notes…
          </div>
        ) : visibleNotes.length === 0 ? (
          !error && <EmptyState filtered={hasFilters} onClear={() => setFilters(EMPTY_FILTERS)} />
        ) : (
          <div className="space-y-8">
            {groupByDay(visibleNotes).map((group) => (
              <section key={group.label} aria-label={group.label}>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {group.label}
                </h2>
                <div className="space-y-3">
                  {group.notes.map((note) => (
                    <NoteCard
                      key={note.id}
                      note={note}
                      typeDef={typeByName[note.type_name]}
                      onDelete={pendingDelete.remove}
                      onEdit={setEditingNote}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>

      {pendingDelete.pendingId && (
        <UndoToast
          key={pendingDelete.pendingId}
          message="Note deleted"
          durationMs={UNDO_SECONDS * 1000}
          onUndo={pendingDelete.undo}
        />
      )}

      {editingNote && (
        <Dialog label="Edit note" onClose={() => !isSavingEdit && setEditingNote(null)}>
          <ReviewForm
            mode="edit"
            draft={editingNote}
            types={types}
            onConfirm={handleEditSave}
            onDiscard={() => setEditingNote(null)}
            isSaving={isSavingEdit}
          />
        </Dialog>
      )}
    </div>
  );
}
