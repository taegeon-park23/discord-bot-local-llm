'use client';

interface DocumentFiltersProps {
    selectedCategory: string;
    selectedDocType: string;
    onCategoryChange: (category: string) => void;
    onDocTypeChange: (docType: string) => void;
    onReset: () => void;
}

export default function DocumentFilters({
    selectedCategory,
    selectedDocType,
    onCategoryChange,
    onDocTypeChange,
    onReset,
}: DocumentFiltersProps) {
    const categories = [
        "All",
        "Development",
        "AI & ML",
        "DevOps & Cloud",
        "Data Science",
        "Security",
        "Design",
        "Trends & News",
        "Marketing & Business",
        "Uncategorized"
    ];

    const docTypes = ["All", "SUMMARY", "DEEP_DIVE", "WEEKLY_REPORT", "OTHER"];

    const hasActiveFilters = selectedCategory !== "All" || selectedDocType !== "All";

    return (
        <div className="flex flex-col md:flex-row gap-4 p-4 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm">
            {/* Category Select */}
            <div className="flex-1">
                <label htmlFor="category-select" className="block text-sm font-medium text-gray-300 mb-2">
                    Category
                </label>
                <select
                    id="category-select"
                    value={selectedCategory}
                    onChange={(e) => onCategoryChange(e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-white focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                >
                    {categories.map((cat) => (
                        <option key={cat} value={cat} className="bg-gray-900 text-white">
                            {cat}
                        </option>
                    ))}
                </select>
            </div>

            {/* Doc Type Select */}
            <div className="flex-1">
                <label htmlFor="doctype-select" className="block text-sm font-medium text-gray-300 mb-2">
                    Document Type
                </label>
                <select
                    id="doctype-select"
                    value={selectedDocType}
                    onChange={(e) => onDocTypeChange(e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-white focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                >
                    {docTypes.map((type) => (
                        <option key={type} value={type} className="bg-gray-900 text-white">
                            {type}
                        </option>
                    ))}
                </select>
            </div>

            {/* Reset Button */}
            <div className="flex items-end">
                <button
                    onClick={onReset}
                    disabled={!hasActiveFilters}
                    className="w-full md:w-auto px-6 py-2 rounded-lg bg-gray-600 text-white font-medium hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    Reset Filters
                </button>
            </div>
        </div>
    );
}
