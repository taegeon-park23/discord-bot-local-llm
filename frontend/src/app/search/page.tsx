'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { searchDocuments } from '@/lib/api';
import { SearchResultItem } from '@/lib/types';
import Link from 'next/link';

export default function SearchPage() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResultItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [offset, setOffset] = useState(0);
    const observerTarget = useRef<HTMLDivElement>(null);
    const currentQuery = useRef('');
    const LIMIT = 10;

    const loadMoreResults = useCallback(async () => {
        if (loading || !hasMore || !currentQuery.current) return;

        setLoading(true);
        try {
            const newResults = await searchDocuments(currentQuery.current, LIMIT, offset);

            if (newResults.length < LIMIT) {
                setHasMore(false);
            }

            setResults(prev => [...prev, ...newResults]);
            setOffset(prev => prev + LIMIT);
        } catch (error) {
            console.error('Error loading more results:', error);
        } finally {
            setLoading(false);
        }
    }, [loading, hasMore, offset]);

    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                if (entries[0].isIntersecting && hasMore && !loading) {
                    loadMoreResults();
                }
            },
            { threshold: 0.1 }
        );

        if (observerTarget.current) {
            observer.observe(observerTarget.current);
        }

        return () => observer.disconnect();
    }, [loadMoreResults, hasMore, loading]);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        // Reset state for new search
        setResults([]);
        setOffset(0);
        setHasMore(true);
        setHasSearched(true);
        currentQuery.current = query;

        setLoading(true);
        try {
            const data = await searchDocuments(query, LIMIT, 0);
            setResults(data);
            setOffset(LIMIT);

            if (data.length < LIMIT) {
                setHasMore(false);
            }
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
            <form onSubmit={handleSearch} className="flex flex-col md:block md:relative gap-3 md:gap-0">
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
                    className="w-full md:w-auto md:absolute md:right-3 md:top-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {loading && offset === 0 ? 'Searching...' : 'Search'}
                </button>
            </form>

            {/* Results */}
            <div className="space-y-6">
                {results.length > 0 ? (
                    <>
                        {results.map((item) => (
                            <div key={`${item.chunk_id}-${item.document_id}`} className="rounded-xl border border-white/10 bg-white/5 p-6 space-y-3 hover:border-white/20 transition-colors">
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
                        ))}

                        {/* Infinite scroll trigger */}
                        <div ref={observerTarget} className="py-4">
                            {loading && (
                                <div className="flex justify-center">
                                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
                                </div>
                            )}
                            {!hasMore && (
                                <div className="text-center text-gray-500 text-sm">
                                    No more results
                                </div>
                            )}
                        </div>
                    </>
                ) : hasSearched && !loading ? (
                    <div className="text-center py-12 text-gray-500">
                        No meaningful matches found. Try rephrasing your query.
                    </div>
                ) : null}
            </div>
        </div>
    );
}
