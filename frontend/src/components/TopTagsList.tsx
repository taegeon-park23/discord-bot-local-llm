'use client';

import { useEffect, useState } from 'react';

interface Tag {
    tag: string;
    count: number;
}

interface TopTagsListProps {
    onTagClick: (tag: string) => void;
    selectedTag?: string;
}

export default function TopTagsList({ onTagClick, selectedTag }: TopTagsListProps) {
    const [tags, setTags] = useState<Tag[]>([]);
    const [loading, setLoading] = useState(false);
    const [hasMore, setHasMore] = useState(true);

    useEffect(() => {
        loadTags(0);
    }, []);

    const loadTags = async (offset: number) => {
        setLoading(true);
        try {
            const res = await fetch(`/api/tags/top?limit=100&offset=${offset}`);
            if (!res.ok) throw new Error('Failed to fetch tags');

            const newTags: Tag[] = await res.json();

            if (newTags.length < 100) {
                setHasMore(false);
            }

            setTags(prev => offset === 0 ? newTags : [...prev, ...newTags]);
        } catch (error) {
            console.error('Error loading tags:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleShowMore = () => {
        if (!loading && hasMore) {
            loadTags(tags.length);
        }
    };

    if (tags.length === 0 && !loading) {
        return (
            <div className="text-sm text-gray-500">
                No tags available yet. Analytics will run automatically.
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">🏷️ Top Tags</h3>

            {/* Tags Grid */}
            <div className="flex flex-wrap gap-2">
                {tags.map((tagItem) => (
                    <button
                        key={tagItem.tag}
                        onClick={() => onTagClick(tagItem.tag)}
                        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all hover:scale-105 ${selectedTag === tagItem.tag
                                ? 'bg-blue-600 text-white border-2 border-blue-400'
                                : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20'
                            }`}
                    >
                        <span>{tagItem.tag}</span>
                        <span className="text-xs opacity-75">({tagItem.count})</span>
                    </button>
                ))}
            </div>

            {/* Show More Button */}
            {hasMore && (
                <button
                    onClick={handleShowMore}
                    disabled={loading}
                    className="w-full rounded-lg bg-white/5 border border-white/10 px-4 py-2 text-sm font-medium text-gray-300 hover:bg-white/10 disabled:opacity-50 transition-colors"
                >
                    {loading ? (
                        <span className="flex items-center justify-center gap-2">
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-400 border-t-transparent"></div>
                            Loading...
                        </span>
                    ) : (
                        'Show More Tags'
                    )}
                </button>
            )}
        </div>
    );
}
