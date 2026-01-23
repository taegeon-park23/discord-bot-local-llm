'use client';

import { useEffect, useState, use } from 'react';
import { fetchDocument, fetchDocumentContent, updateDocumentContent } from '@/lib/api';
import { Document } from '@/lib/types';
import { useRouter } from 'next/navigation';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

export default function EditDocumentPage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params);
    const id = parseInt(resolvedParams.id);

    const router = useRouter();
    const [doc, setDoc] = useState<Document | null>(null);
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [showMobilePreview, setShowMobilePreview] = useState(false);

    useEffect(() => {
        Promise.all([
            fetchDocument(id),
            fetchDocumentContent(id)
        ])
            .then(([docData, contentData]) => {
                setDoc(docData);
                setContent(contentData.content);
            })
            .catch((err) => {
                console.error(err);
                alert('Failed to load document');
            })
            .finally(() => setLoading(false));
    }, [id]);

    const handleSave = async () => {
        if (!doc) return;
        setSaving(true);
        try {
            await updateDocumentContent(doc.id, content);
            alert('Saved successfully!');
            router.push(`/documents/${doc.id}`); // Go back to view page on save
        } catch (err) {
            console.error(err);
            alert('Failed to save');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;
    if (!doc) return <div className="text-center py-20 text-red-400">Document not found</div>;

    return (
        <div className="h-[calc(100vh-100px)] flex flex-col gap-4">
            {/* Header - Mobile Responsive */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 shrink-0">
                <div>
                    <h1 className="text-xl md:text-2xl font-bold text-white">Editing: {doc.title}</h1>
                    <p className="text-sm text-gray-400 truncate max-w-[300px] md:max-w-none">{doc.local_file_path}</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => router.push(`/documents/${doc.id}`)}
                        className="flex-1 sm:flex-none px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex-1 sm:flex-none px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 min-h-0">
                {/* Editor Pane */}
                <div className="rounded-xl border border-white/10 bg-black/20 overflow-hidden flex flex-col">
                    <div className="bg-white/5 px-4 py-2 border-b border-white/10 text-xs text-gray-400 uppercase tracking-wider font-semibold">
                        Editor
                    </div>
                    <textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        className="flex-1 w-full bg-transparent p-6 text-gray-200 font-mono text-sm focus:outline-none resize-none"
                        spellCheck={false}
                        placeholder="Type your markdown here..."
                    />
                </div>

                {/* Preview Pane - Desktop Only */}
                <div className="hidden md:flex rounded-xl border border-white/10 bg-white/5 overflow-hidden flex-col">
                    <div className="bg-white/5 px-4 py-2 border-b border-white/10 text-xs text-gray-400 uppercase tracking-wider font-semibold">
                        Preview
                    </div>
                    <div className="flex-1 overflow-auto p-6 prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                            {content.replace(/\n{3,}/g, (match) => '\n' + '&nbsp;\n'.repeat(match.length - 2) + '\n')}
                        </ReactMarkdown>
                    </div>
                </div>
            </div>

            {/* Floating Preview Button - Mobile Only */}
            <button
                onClick={() => setShowMobilePreview(true)}
                className="md:hidden fixed bottom-6 right-6 w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-500/50 flex items-center justify-center transition-all hover:scale-110 z-40"
                aria-label="Preview"
            >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
            </button>

            {/* Mobile Preview Overlay */}
            {showMobilePreview && (
                <div className="md:hidden fixed inset-0 bg-black/95 backdrop-blur-sm z-50 flex flex-col">
                    {/* Overlay Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-white/5">
                        <h2 className="text-lg font-semibold text-white">Preview</h2>
                        <button
                            onClick={() => setShowMobilePreview(false)}
                            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
                        >
                            Close
                        </button>
                    </div>
                    {/* Overlay Content */}
                    <div className="flex-1 overflow-auto p-6 prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                            {content.replace(/\n{3,}/g, (match) => '\n' + '&nbsp;\n'.repeat(match.length - 2) + '\n')}
                        </ReactMarkdown>
                    </div>
                </div>
            )}
        </div>
    );
}
