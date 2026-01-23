'use client';

import { useEffect, useState } from 'react';
import { fetchDocuments, fetchStats } from '@/lib/api';
import { Document, UploadStatus } from '@/lib/types';
import Link from 'next/link';

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalDocs, setTotalDocs] = useState(0);
    const limit = 50;

    useEffect(() => {
        // Fetch stats for total count
        fetchStats().then(stats => setTotalDocs(stats.total_documents)).catch(console.error);
    }, []);

    useEffect(() => {
        setLoading(true);
        const skip = (currentPage - 1) * limit;
        fetchDocuments(skip, limit)
            .then(setDocuments)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [currentPage]);

    const totalPages = Math.ceil(totalDocs / limit);

    const handlePrev = () => {
        if (currentPage > 1) setCurrentPage(p => p - 1);
    };

    const handleNext = () => {
        if (currentPage < totalPages) setCurrentPage(p => p + 1);
    };

    if (loading && documents.length === 0) {
        return <div className="flex h-96 items-center justify-center text-gray-400">Loading documents...</div>;
    }

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-white">Documents</h1>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-400">Total: {totalDocs}</span>
                    <button
                        onClick={() => setCurrentPage(1)}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
                        Refresh List
                    </button>
                </div>
            </div>

            <div className="overflow-hidden rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm">
                <table className="w-full text-left text-sm text-gray-400">
                    <thead className="bg-white/5 text-gray-200">
                        <tr>
                            <th className="px-6 py-4 font-medium">Title</th>
                            <th className="px-6 py-4 font-medium">Type</th>
                            <th className="px-6 py-4 font-medium">Status</th>
                            <th className="px-6 py-4 font-medium">Date</th>
                            <th className="px-6 py-4 font-medium text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {documents.map((doc) => (
                            <tr key={doc.id} className="hover:bg-white/5 transition-colors">
                                <td className="px-6 py-4 font-medium text-white max-w-sm truncate">{doc.title}</td>
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

            {/* Pagination Controls */}
            <div className="flex items-center justify-between border-t border-white/10 pt-4">
                <button
                    onClick={handlePrev}
                    disabled={currentPage === 1}
                    className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Previous
                </button>
                <span className="text-sm text-gray-400">
                    Page {currentPage} of {totalPages || 1}
                </span>
                <button
                    onClick={handleNext}
                    disabled={currentPage >= totalPages}
                    className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Next
                </button>
            </div>
        </div>
    );
}
