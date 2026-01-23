'use client';

import { useEffect, useState, use } from 'react';
import { fetchDocument, fetchDocumentContent } from '@/lib/api';
import { Document } from '@/lib/types';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

export default function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = use(params);
    const id = parseInt(resolvedParams.id);
    const router = useRouter();

    const [doc, setDoc] = useState<Document | null>(null);
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(true);

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

    if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;
    if (!doc) return <div className="text-center py-20 text-red-400">Document not found</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-20">
            {/* Header - Mobile Responsive */}
            <div className="flex flex-col gap-4 border-b border-white/10 pb-6">
                <div>
                    <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">{doc.title}</h1>
                    <div className="flex flex-wrap gap-2 text-sm text-gray-400">
                        <span className="px-2 py-1 rounded bg-white/5">{doc.doc_type}</span>
                        <span className="px-2 py-1 rounded bg-white/5 truncate max-w-[200px] md:max-w-none">{doc.local_file_path}</span>
                    </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-3">
                    <button
                        onClick={() => router.back()}
                        className="w-full sm:w-auto px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition-colors"
                    >
                        Back
                    </button>
                    <Link
                        href={`/documents/${doc.id}/edit`}
                        className="w-full sm:w-auto px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium transition-colors text-center"
                    >
                        Edit Document
                    </Link>
                </div>
            </div>

            {/* Content Viewer */}
            <article className="prose prose-invert prose-lg max-w-none 
                prose-headings:font-bold prose-h1:text-3xl prose-h2:text-2xl 
                prose-a:text-blue-400 hover:prose-a:text-blue-300
                prose-code:text-pink-300 prose-code:bg-white/5 prose-code:rounded prose-code:px-1 prose-code:before:content-none prose-code:after:content-none
                prose-pre:bg-white/5 prose-pre:border prose-pre:border-white/10
                ">
                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                    {content.replace(/\n{3,}/g, (match) => '\n' + '&nbsp;\n'.repeat(match.length - 2) + '\n')}
                </ReactMarkdown>
            </article>
        </div>
    );
}
