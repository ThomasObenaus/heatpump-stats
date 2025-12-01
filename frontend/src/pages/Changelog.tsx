import React, { useEffect, useState } from "react";
import axios from "axios";
import Layout from "../components/Layout";
import DiffViewer from "../components/DiffViewer";
import type { ChangelogEntry } from "../types";

interface EditingState {
  entryId: number;
  name: string;
}

interface EditingNoteState {
  entryId: number;
  note: string;
}

const Changelog: React.FC = () => {
  const [entries, setEntries] = useState<ChangelogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [editing, setEditing] = useState<EditingState | null>(null);
  const [editingNote, setEditingNote] = useState<EditingNoteState | null>(null);
  const [saving, setSaving] = useState<boolean>(false);

  const fetchChangelog = async () => {
    try {
      const response = await axios.get<ChangelogEntry[]>("/api/changelog");
      setEntries(response.data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch changelog:", err);
      setError("Failed to load changelog");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    setSubmitting(true);
    try {
      await axios.post("/api/changelog", { message: newMessage });
      setNewMessage("");
      fetchChangelog(); // Refresh list
    } catch (err) {
      console.error("Failed to add note:", err);
      alert("Failed to add note");
    } finally {
      setSubmitting(false);
    }
  };

  const startEditing = (entry: ChangelogEntry) => {
    if (entry.id) {
      setEditing({ entryId: entry.id, name: entry.name || "" });
    }
  };

  const cancelEditing = () => {
    setEditing(null);
  };

  const saveName = async () => {
    if (!editing) return;

    setSaving(true);
    try {
      await axios.patch(`/api/changelog/${editing.entryId}/name`, { name: editing.name });
      // Update local state
      setEntries((prev) => prev.map((e) => (e.id === editing.entryId ? { ...e, name: editing.name } : e)));
      setEditing(null);
    } catch (err) {
      console.error("Failed to update name:", err);
      alert("Failed to save name");
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      saveName();
    } else if (e.key === "Escape") {
      cancelEditing();
    }
  };

  const startEditingNote = (entry: ChangelogEntry) => {
    if (entry.id) {
      setEditingNote({ entryId: entry.id, note: entry.message || "" });
    }
  };

  const cancelEditingNote = () => {
    setEditingNote(null);
  };

  const saveNote = async () => {
    if (!editingNote) return;

    setSaving(true);
    try {
      await axios.patch(`/api/changelog/${editingNote.entryId}/note`, { note: editingNote.note });
      // Update local state
      setEntries((prev) => prev.map((e) => (e.id === editingNote.entryId ? { ...e, message: editingNote.note } : e)));
      setEditingNote(null);
    } catch (err) {
      console.error("Failed to update note:", err);
      alert("Failed to save note");
    } finally {
      setSaving(false);
    }
  };

  const handleNoteKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      saveNote();
    } else if (e.key === "Escape") {
      cancelEditingNote();
    }
  };

  useEffect(() => {
    fetchChangelog();
  }, []);

  return (
    <Layout>
      <div className="w-full">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">System Changelog</h1>

        {/* Add Note Form */}
        <div className="bg-white shadow sm:rounded-lg mb-8 p-6 max-w-2xl">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Add Note</h3>
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="message" className="sr-only">
                Message
              </label>
              <textarea
                id="message"
                rows={3}
                className="shadow-sm block w-full focus:ring-blue-500 focus:border-blue-500 sm:text-sm border border-gray-300 rounded-md p-2"
                placeholder="Enter a manual note about system changes..."
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={submitting || !newMessage.trim()}
                className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                  submitting || !newMessage.trim() ? "opacity-50 cursor-not-allowed" : ""
                }`}
              >
                {submitting ? "Adding..." : "Add Note"}
              </button>
            </div>
          </form>
        </div>

        {/* Timeline */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : error ? (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        ) : (
          <div className="flow-root">
            <ul className="-mb-8">
              {entries.map((entry, entryIdx) => (
                <li key={entry.id || entryIdx}>
                  <div className="relative pb-8">
                    {entryIdx !== entries.length - 1 ? (
                      <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true" />
                    ) : null}
                    <div className="relative flex space-x-3">
                      <div className="flex-shrink-0">
                        <span
                          className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${
                            entry.category === "manual" ? "bg-blue-500" : entry.category === "system" ? "bg-green-500" : "bg-gray-500"
                          }`}
                        >
                          {/* Icon based on category */}
                          {entry.category === "manual" ? (
                            <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                              />
                            </svg>
                          ) : (
                            <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                              />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                          )}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1 pt-1.5">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            {/* Editable Name */}
                            {editing && editing.entryId === entry.id ? (
                              <div className="flex items-center space-x-2 mb-1">
                                <input
                                  type="text"
                                  value={editing.name}
                                  onChange={(e) => setEditing({ entryId: editing.entryId, name: e.target.value.slice(0, 100) })}
                                  onKeyDown={handleKeyDown}
                                  maxLength={100}
                                  className="flex-1 text-sm font-semibold text-gray-900 border border-blue-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  placeholder="Enter a name for this change..."
                                  autoFocus
                                  disabled={saving}
                                />
                                <button
                                  onClick={saveName}
                                  disabled={saving}
                                  className="text-green-600 hover:text-green-800 p-1"
                                  title="Save"
                                >
                                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                  </svg>
                                </button>
                                <button
                                  onClick={cancelEditing}
                                  disabled={saving}
                                  className="text-gray-500 hover:text-gray-700 p-1"
                                  title="Cancel"
                                >
                                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                  </svg>
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center space-x-2 mb-1 group">
                                {entry.name ? (
                                  <span className="text-sm font-semibold text-gray-900">{entry.name}</span>
                                ) : (
                                  <span className="text-sm text-gray-400 italic">No name</span>
                                )}
                                <button
                                  onClick={() => startEditing(entry)}
                                  className="text-gray-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                                  title="Edit name"
                                >
                                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                                    />
                                  </svg>
                                </button>
                              </div>
                            )}
                            {/* Editable Note */}
                            {editingNote && editingNote.entryId === entry.id ? (
                              <div className="flex items-start space-x-2">
                                <textarea
                                  value={editingNote.note}
                                  onChange={(e) => setEditingNote({ entryId: editingNote.entryId, note: e.target.value.slice(0, 1000) })}
                                  onKeyDown={handleNoteKeyDown}
                                  maxLength={1000}
                                  rows={2}
                                  className="flex-1 text-sm text-gray-500 border border-blue-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  placeholder="Enter a note..."
                                  autoFocus
                                  disabled={saving}
                                />
                                <button
                                  onClick={saveNote}
                                  disabled={saving}
                                  className="text-green-600 hover:text-green-800 p-1"
                                  title="Save"
                                >
                                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                  </svg>
                                </button>
                                <button
                                  onClick={cancelEditingNote}
                                  disabled={saving}
                                  className="text-gray-500 hover:text-gray-700 p-1"
                                  title="Cancel"
                                >
                                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                  </svg>
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center space-x-2 group">
                                <p className="text-sm text-gray-500">
                                  {entry.message} <span className="font-medium text-gray-900">by {entry.author}</span>
                                </p>
                                <button
                                  onClick={() => startEditingNote(entry)}
                                  className="text-gray-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                                  title="Edit note"
                                >
                                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                                    />
                                  </svg>
                                </button>
                              </div>
                            )}
                          </div>
                          <div className="text-right text-sm whitespace-nowrap text-gray-500 ml-4">
                            <time dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleString()}</time>
                          </div>
                        </div>
                        {entry.details && <DiffViewer details={entry.details} />}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Changelog;
