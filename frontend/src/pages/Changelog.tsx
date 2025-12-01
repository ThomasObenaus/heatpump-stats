import React, { useEffect, useState } from "react";
import axios from "axios";
import Layout from "../components/Layout";
import type { ChangelogEntry } from "../types";

const Changelog: React.FC = () => {
  const [entries, setEntries] = useState<ChangelogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);

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

  useEffect(() => {
    fetchChangelog();
  }, []);

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">System Changelog</h1>

        {/* Add Note Form */}
        <div className="bg-white shadow sm:rounded-lg mb-8 p-6">
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
                      <div>
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
                      <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                        <div>
                          <p className="text-sm text-gray-500">
                            {entry.message} <span className="font-medium text-gray-900">by {entry.author}</span>
                          </p>
                          {entry.details && (
                            <div className="mt-2 text-sm text-gray-700 bg-gray-50 p-2 rounded border border-gray-200 font-mono whitespace-pre-wrap">
                              {entry.details}
                            </div>
                          )}
                        </div>
                        <div className="text-right text-sm whitespace-nowrap text-gray-500">
                          <time dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleString()}</time>
                        </div>
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
