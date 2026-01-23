'use client';

import { useEffect, useState, use } from 'react';
import { fetchDocument, fetchDocumentContent, updateDocumentContent } from '@/lib/api';
import { Document } from '@/lib/types';
import { useRouter } from 'next/navigation';

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
            router.refresh();
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
        <div className="max-w-5xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">{doc.title}</h1>
                    <p className="text-sm text-gray-400">{doc.local_file_path}</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => router.back()}
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

            <div className="h-[70vh] rounded-xl border border-white/10 bg-black/20 overflow-hidden">
                <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full h-full bg-transparent p-6 text-gray-200 font-mono text-sm focus:outline-none resize-none"
                    spellCheck={false}
                />
            </div>
        </div>
    );
}
