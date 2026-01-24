'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { fetchDocuments, fetchStats, generateTagsForDocument, deleteDocument } from '@/lib/api';
import { Document, UploadStatus } from '@/lib/types';
import Link from 'next/link';
import DocumentFilters from '@/components/DocumentFilters';
import TopTagsList from '@/components/TopTagsList';

import { useRouter } from 'next/navigation';

export default function DocumentsPage() {
    const router = useRouter(); // Initialize router
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);
    const [totalDocs, setTotalDocs] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [skip, setSkip] = useState(0);
    const [selectedCategory, setSelectedCategory] = useState<string>("All");
    const [selectedDocType, setSelectedDocType] = useState<string>("All");
    const [selectedTag, setSelectedTag] = useState<string>("");
    const observerTarget = useRef<HTMLDivElement>(null);
    const loadingRef = useRef(false);
    const LIMIT = 20;
    const [generatingTagDocId, setGeneratingTagDocId] = useState<number | null>(null);

    const loadDocuments = useCallback(async (currentSkip: number) => {
        if (loadingRef.current) return;

        loadingRef.current = true;
        setLoading(true);
        try {
            const options = {
                category: selectedCategory !== "All" ? selectedCategory : undefined,
                docType: selectedDocType !== "All" ? selectedDocType : undefined,
                tag: selectedTag || undefined,
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
            loadingRef.current = false;
        }
    }, [selectedCategory, selectedDocType, selectedTag]);

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
        fetchStats({
            category: selectedCategory,
            docType: selectedDocType
        }).then(stats => setTotalDocs(stats.total_documents)).catch(console.error);
    };

    // 필터 변경 시 문서 목록 초기화 및 재로드
    useEffect(() => {
        setDocuments([]);
        setSkip(0);
        setHasMore(true);
        loadDocuments(0);

        // Update stats when filter changes
        fetchStats({
            category: selectedCategory !== "All" ? selectedCategory : undefined,
            docType: selectedDocType !== "All" ? selectedDocType : undefined
        }).then(stats => setTotalDocs(stats.total_documents)).catch(console.error);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedCategory, selectedDocType, selectedTag]);

    const handleResetFilters = () => {
        setSelectedCategory("All");
        setSelectedDocType("All");
        setSelectedTag("");
    };

    const handleTagClick = (tag: string) => {
        if (selectedTag === tag) {
            // 이미 선택된 태그를 다시 클릭하면 필터 해제
            setSelectedTag("");
        } else {
            setSelectedTag(tag);
        }
    };

    const handleRowDoubleClick = (docId: number) => {
        router.push(`/documents/${docId}`);
    };

    const handleGenerateTags = async (docId: number, event?: React.MouseEvent) => {
        if (event) event.stopPropagation();

        if (!confirm('이 문서의 태그를 생성하시겠습니까?')) return;

        setGeneratingTagDocId(docId);

        try {
            const result = await generateTagsForDocument(docId);
            if (result.success) {
                // Update local state
                setDocuments(prev => prev.map(doc =>
                    doc.id === docId ? { ...doc, tags: result.tags } : doc
                ));
                alert(`✅ ${result.tags.length}개의 태그가 생성되었습니다!`);
            } else {
                alert('⚠️ ' + result.message);
            }
        } catch (error) {
            console.error('Tag generation failed:', error);
            alert('❌ 태그 생성 중 오류가 발생했습니다.');
        } finally {
            setGeneratingTagDocId(null);
        }
    };

    const handleDeleteDocument = async (docId: number, event?: React.MouseEvent) => {
        if (event) event.stopPropagation();

        if (!confirm('⚠️ 이 문서를 삭제하시겠습니까?\n\nDB 레코드, 로컬 파일, 벡터 임베딩이 모두 삭제됩니다.')) return;

        try {
            const result = await deleteDocument(docId);
            if (result.success) {
                // Remove from local state
                setDocuments(prev => prev.filter(doc => doc.id !== docId));
                setTotalDocs(prev => prev - 1);
                alert('✅ 문서가 삭제되었습니다.');
            }
        } catch (error) {
            console.error('Delete failed:', error);
            alert('❌ 문서 삭제 중 오류가 발생했습니다.');
        }
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

            {/* Top Tags List */}
            <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-6">
                <TopTagsList onTagClick={handleTagClick} selectedTag={selectedTag} />
            </div>

            {/* Desktop Table View - Hidden on Mobile */}
            {/* Removed overflow-hidden to allow tooltips to popup properly */}
            <div className="hidden md:block rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm">
                <table className="w-full text-left text-sm text-gray-400">
                    <thead className="bg-white/5 text-gray-200">
                        <tr>
                            <th className="px-6 py-4 font-medium first:rounded-tl-xl">Title</th>
                            <th className="px-6 py-4 font-medium">Category</th>
                            <th className="px-6 py-4 font-medium">Tags</th>
                            <th className="px-6 py-4 font-medium">Type</th>
                            <th className="px-6 py-4 font-medium">Status</th>
                            <th className="px-6 py-4 font-medium">Date</th>
                            <th className="px-6 py-4 font-medium text-right first:rounded-tr-xl">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {documents.map((doc) => (
                            <tr
                                key={`doc-pc-${doc.id}-${doc.title}`}
                                className="hover:bg-white/5 transition-colors cursor-pointer"
                                onDoubleClick={() => handleRowDoubleClick(doc.id)}
                            >
                                <td className="px-6 py-4 font-medium text-white max-w-sm truncate">{doc.title}</td>
                                <td className="px-6 py-4">
                                    {doc.category && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation(); // Prevent row double click
                                                setSelectedCategory(doc.category!);
                                            }}
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
                                    {doc.tags && doc.tags.length > 0 ? (
                                        <div className="relative group flex flex-wrap gap-1">
                                            {/* Show only first 3 tags normally */}
                                            {doc.tags.slice(0, 3).map((tag, idx) => (
                                                <span key={`${doc.id}-tag-${idx}`} className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                                    {tag}
                                                </span>
                                            ))}

                                            {/* If more than 3, show count badge */}
                                            {doc.tags.length > 3 && (
                                                <span className="inline-flex items-center px-1.5 py-0.5 text-xs text-gray-500 cursor-help border border-transparent hover:border-gray-500/30 rounded-full">
                                                    +{doc.tags.length - 3}
                                                </span>
                                            )}

                                            {/* Floating Popup on Hover - Shows ALL tags */}
                                            <div className="absolute left-0 top-full mt-2 w-64 p-3 bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 pointer-events-none group-hover:pointer-events-auto">
                                                <div className="flex flex-wrap gap-1.5">
                                                    {doc.tags.map((tag, idx) => (
                                                        <span key={`popup-${doc.id}-${tag}-${idx}`} className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                                            {tag}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={(e) => handleGenerateTags(doc.id, e)}
                                            disabled={generatingTagDocId === doc.id}
                                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 hover:bg-yellow-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {generatingTagDocId === doc.id ? (
                                                <>
                                                    <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                    </svg>
                                                    생성 중...
                                                </>
                                            ) : (
                                                <>
                                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                                    </svg>
                                                    태그 생성
                                                </>
                                            )}
                                        </button>
                                    )}
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
                                    <div className="flex items-center justify-end gap-3">
                                        <Link href={`/documents/${doc.id}`} className="text-blue-400 hover:text-blue-300">
                                            View
                                        </Link>
                                        <button
                                            onClick={(e) => handleDeleteDocument(doc.id, e)}
                                            className="text-red-400 hover:text-red-300 transition-colors"
                                            title="Delete document"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>
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

                        {/* Tags Row */}\r
                        {doc.tags && doc.tags.length > 0 ? (
                            <div className="flex flex-wrap gap-2 mb-3">
                                {doc.tags.map((tag, idx) => (
                                    <span key={`${doc.id}-mobile-tag-${idx}`} className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        ) : (
                            <div className="mb-3">
                                <button
                                    onClick={(e) => handleGenerateTags(doc.id, e)}
                                    disabled={generatingTagDocId === doc.id}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 hover:bg-yellow-500/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {generatingTagDocId === doc.id ? (
                                        <>
                                            <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                            생성 중...
                                        </>
                                    ) : (
                                        <>
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                            </svg>
                                            태그 생성
                                        </>
                                    )}
                                </button>
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
                        <div className="flex items-center justify-between gap-2">
                            <span className="text-xs text-gray-400">
                                {new Date(doc.created_at).toLocaleDateString()}
                            </span>
                            <div className="flex items-center gap-2">
                                <Link
                                    href={`/documents/${doc.id}`}
                                    className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
                                >
                                    View
                                </Link>
                                <button
                                    onClick={() => handleDeleteDocument(doc.id)}
                                    className="p-2 rounded-lg bg-red-600/10 text-red-400 hover:bg-red-600/20 transition-colors"
                                    title="Delete document"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                </button>
                            </div>
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
