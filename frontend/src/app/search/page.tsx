'use client';

import { useState } from 'react';
import { searchDocuments } from '@/lib/api';
import { SearchResultItem } from '@/lib/types';
import Link from 'next/link';

export default function SearchPage() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResultItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setHasSearched(true);
        try {
            const data = await searchDocuments(query);
            setResults(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-white mb-8">Semantic Search</h1>

            {/* Search Input */}
            <form onSubmit={handleSearch} className="relative">
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask a question about your documents..."
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-6 py-4 text-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
                />
                <button
                    type="submit"
                    disabled={loading || !query.trim()}
                    className="absolute right-3 top-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {loading ? 'Searching...' : 'Search'}
                </button>
            </form>

            {/* Results */}
            <div className="space-y-6">
                {loading ? (
                    <div className="space-y-4">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="h-32 rounded-xl bg-white/5 animate-pulse" />
                        ))}
                    </div>
                ) : results.length > 0 ? (
                    results.map((item) => (
                        <div key={item.chunk_id} className="rounded-xl border border-white/10 bg-white/5 p-6 space-y-3 hover:border-white/20 transition-colors">
                            <div className="flex items-center justify-between">
                                <Link
                                    href={`/documents/${item.document_id}`}
                                    className="text-lg font-semibold text-blue-400 hover:text-blue-300"
                                >
                                    {item.document_title}
                                </Link>
                                <span className="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded">
                                    Chunk #{item.chunk_id}
                                </span>
                            </div>
                            <p className="text-gray-300 leading-relaxed text-sm">
                                ...{item.content}...
                            </p>
                            {item.score !== "N/A" && (
                                <div className="text-xs text-gray-500">
                                    Score: {item.score}
                                </div>
                            )}
                        </div>
                    ))
                ) : hasSearched && (
                    <div className="text-center py-12 text-gray-500">
                        No meaningful matches found. Try rephrasing your query.
                    </div>
                )}
            </div>
        </div>
    );
}
