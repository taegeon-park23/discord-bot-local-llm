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
            <div className="flex items-center justify-between shrink-0">
                <div>
                    <h1 className="text-2xl font-bold text-white">Editing: {doc.title}</h1>
                    <p className="text-sm text-gray-400">{doc.local_file_path}</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => router.push(`/documents/${doc.id}`)}
                        className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors disabled:opacity-50"
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

                {/* Preview Pane */}
                <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden flex flex-col">
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
        </div>
    );
}
