'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { fetchDocuments, fetchStats } from '@/lib/api';
import { Document, UploadStatus } from '@/lib/types';
import Link from 'next/link';
import DocumentFilters from '@/components/DocumentFilters';

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);
    const [totalDocs, setTotalDocs] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [skip, setSkip] = useState(0);
    const [selectedCategory, setSelectedCategory] = useState<string>("All");
    const [selectedDocType, setSelectedDocType] = useState<string>("All");
    const observerTarget = useRef<HTMLDivElement>(null);
    const LIMIT = 20;

    useEffect(() => {
        // Fetch stats for total count
        fetchStats().then(stats => setTotalDocs(stats.total_documents)).catch(console.error);

        // Load initial documents
        loadDocuments(0);
    }, []);

    const loadDocuments = async (currentSkip: number) => {
        if (loading) return;

        setLoading(true);
        try {
            const options = {
                category: selectedCategory !== "All" ? selectedCategory : undefined,
                docType: selectedDocType !== "All" ? selectedDocType : undefined,
            };

            const newDocs = await fetchDocuments(currentSkip, LIMIT, options);

            if (newDocs.length < LIMIT) {
                setHasMore(false);
            }

            setDocuments(prev => currentSkip === 0 ? newDocs : [...prev, ...newDocs]);
            setSkip(currentSkip + LIMIT);
        } catch (error) {
            console.error('Error loading documents:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadMoreDocuments = useCallback(() => {
        if (!loading && hasMore) {
            loadDocuments(skip);
        }
    }, [loading, hasMore, skip]);

    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                if (entries[0].isIntersecting && hasMore && !loading) {
                    loadMoreDocuments();
                }
            },
            { threshold: 0.1 }
        );

        if (observerTarget.current) {
            observer.observe(observerTarget.current);
        }

        return () => observer.disconnect();
    }, [loadMoreDocuments, hasMore, loading]);

    const handleRefresh = () => {
        setDocuments([]);
        setSkip(0);
        setHasMore(true);
        loadDocuments(0);
    };

    const handleFilterChange = useCallback(() => {
        setDocuments([]);
        setSkip(0);
        setHasMore(true);
        loadDocuments(0);
    }, [selectedCategory, selectedDocType]);

    useEffect(() => {
        handleFilterChange();
    }, [selectedCategory, selectedDocType]);

    const handleResetFilters = () => {
        setSelectedCategory("All");
        setSelectedDocType("All");
    };

    return (
        <div className="space-y-8">
            {/* Header - Mobile Responsive */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <h1 className="text-3xl font-bold text-white">Documents</h1>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-400">Total: {totalDocs}</span>
                    <button
                        onClick={handleRefresh}
                        disabled={loading && documents.length === 0}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
                        Refresh List
                    </button>
                </div>
            </div>

            {/* Filters */}
            <DocumentFilters
                selectedCategory={selectedCategory}
                selectedDocType={selectedDocType}
                onCategoryChange={setSelectedCategory}
                onDocTypeChange={setSelectedDocType}
                onReset={handleResetFilters}
            />

            {/* Desktop Table View - Hidden on Mobile */}
            <div className="hidden md:block overflow-hidden rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm">
                <table className="w-full text-left text-sm text-gray-400">
                    <thead className="bg-white/5 text-gray-200">
                        <tr>
                            <th className="px-6 py-4 font-medium">Title</th>
                            <th className="px-6 py-4 font-medium">Category</th>
                            <th className="px-6 py-4 font-medium">Tags</th>
                            <th className="px-6 py-4 font-medium">Type</th>
                            <th className="px-6 py-4 font-medium">Status</th>
                            <th className="px-6 py-4 font-medium">Date</th>
                            <th className="px-6 py-4 font-medium text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {documents.map((doc) => (
                            <tr key={`doc-pc-${doc.id}-${doc.title}`} className="hover:bg-white/5 transition-colors">
                                <td className="px-6 py-4 font-medium text-white max-w-sm truncate">{doc.title}</td>
                                <td className="px-6 py-4">
                                    {doc.category && (
                                        <button
                                            onClick={() => setSelectedCategory(doc.category!)}
                                            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors cursor-pointer ${doc.category === "Uncategorized"
                                                ? 'bg-gray-500/10 text-gray-400 border border-gray-500/20 hover:bg-gray-500/20'
                                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20'
                                                }`}
                                        >
                                            {doc.category}
                                        </button>
                                    )}
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex flex-wrap gap-1">
                                        {doc.tags && doc.tags.slice(0, 3).map((tag, idx) => (
                                            <span key={`${doc.id}-tag-${idx}`} className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                                {tag}
                                            </span>
                                        ))}
                                        {doc.tags && doc.tags.length > 3 && (
                                            <span className="text-xs text-gray-500">+{doc.tags.length - 3}</span>
                                        )}
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium 
                    ${doc.doc_type === 'SUMMARY' ? 'bg-blue-500/10 text-blue-400' :
                                            doc.doc_type === 'DEEP_DIVE' ? 'bg-purple-500/10 text-purple-400' : 'bg-gray-500/10 text-gray-400'}`}>
                                        {doc.doc_type}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium 
                    ${doc.gdrive_upload_status === 'SUCCESS' ? 'bg-green-500/10 text-green-400' :
                                            doc.gdrive_upload_status === 'FAILED' ? 'bg-red-500/10 text-red-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                                        {doc.gdrive_upload_status}
                                    </span>
                                </td>
                                <td className="px-6 py-4">{new Date(doc.created_at).toLocaleDateString()}</td>
                                <td className="px-6 py-4 text-right">
                                    <Link href={`/documents/${doc.id}`} className="text-blue-400 hover:text-blue-300">
                                        View
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Mobile Card View - Visible on Mobile Only */}
            <div className="md:hidden space-y-4">
                {documents.map((doc) => (
                    <div
                        key={`doc-mobile-${doc.id}-${doc.title}`}
                        className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-4 hover:border-white/20 transition-all"
                    >
                        {/* Category Badge */}
                        {doc.category && (
                            <button
                                onClick={() => setSelectedCategory(doc.category!)}
                                className={`inline-flex items-center rounded-full px-2.5 py-1 mb-2 text-xs font-semibold transition-colors cursor-pointer ${doc.category === "Uncategorized"
                                    ? 'bg-gray-500/20 text-gray-400 border border-gray-500/30 hover:bg-gray-500/30'
                                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30'
                                    }`}
                            >
                                {doc.category === "Uncategorized" ? "🔖" : "📁"} {doc.category}
                            </button>
                        )}

                        {/* Title */}
                        <h3 className="font-semibold text-white text-base mb-3 line-clamp-2">
                            {doc.title}
                        </h3>

                        {/* Tags Row */}
                        {doc.tags && doc.tags.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-3">
                                {doc.tags.map((tag, idx) => (
                                    <span key={`${doc.id}-mobile-tag-${idx}`} className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        )}

                        {/* Type and Status Tags */}
                        <div className="flex flex-wrap gap-2 mb-3">
                            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium 
                                ${doc.doc_type === 'SUMMARY' ? 'bg-blue-500/10 text-blue-400' :
                                    doc.doc_type === 'DEEP_DIVE' ? 'bg-purple-500/10 text-purple-400' : 'bg-gray-500/10 text-gray-400'}`}>
                                {doc.doc_type}
                            </span>
                            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium 
                                ${doc.gdrive_upload_status === 'SUCCESS' ? 'bg-green-500/10 text-green-400' :
                                    doc.gdrive_upload_status === 'FAILED' ? 'bg-red-500/10 text-red-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                                {doc.gdrive_upload_status}
                            </span>
                        </div>

                        {/* Date and Action Row */}
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-400">
                                {new Date(doc.created_at).toLocaleDateString()}
                            </span>
                            <Link
                                href={`/documents/${doc.id}`}
                                className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
                            >
                                View
                            </Link>
                        </div>
                    </div>
                ))}
            </div>

            {/* Infinite scroll trigger and loading indicator */}
            <div ref={observerTarget} className="py-8">
                {loading && (
                    <div className="flex justify-center">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
                    </div>
                )}
                {!hasMore && documents.length > 0 && (
                    <div className="text-center text-gray-500 text-sm">
                        All documents loaded ({documents.length} / {totalDocs})
                    </div>
                )}
                {documents.length === 0 && !loading && (
                    <div className="text-center py-12">
                        <div className="text-gray-500 text-lg mb-2">
                            {selectedCategory !== "All" || selectedDocType !== "All"
                                ? "No documents found matching current filters"
                                : "No documents found"}
                        </div>
                        {(selectedCategory !== "All" || selectedDocType !== "All") && (
                            <button
                                onClick={handleResetFilters}
                                className="mt-4 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
                            >
                                Reset Filters
                            </button>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
