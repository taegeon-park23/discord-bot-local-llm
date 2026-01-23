import Link from "next/link";

export default function Navbar() {
    return (
        <nav className="sticky top-0 z-50 w-full border-b border-white/10 bg-black/50 backdrop-blur-xl">
            <div className="container mx-auto flex h-16 items-center justify-between px-4">
                <Link href="/" className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent hover:opacity-80 transition-opacity">
                    KnowledgeBot
                </Link>
                <div className="flex gap-6 text-sm font-medium text-gray-300">
                    <Link href="/" className="hover:text-white transition-colors">Dashboard</Link>
                    <Link href="/documents" className="hover:text-white transition-colors">Documents</Link>
                    <Link href="/search" className="hover:text-white transition-colors text-blue-400">Search</Link>
                    <Link href="/settings" className="hover:text-white transition-colors">Settings</Link>
                </div>
            </div>
        </nav>
    );
}
