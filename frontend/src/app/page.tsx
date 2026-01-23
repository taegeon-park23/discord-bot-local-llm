'use client';

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchStats } from "@/lib/api";
import { DashboardStats } from "@/lib/types";

export default function Home() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch((err) => {
        console.error(err);
        setError(true);
      });
  }, []);

  const getDisplayValue = (val: number | undefined) => {
    if (stats && val !== undefined) return val.toLocaleString();
    if (error) return "N/A";
    return "...";
  };

  const statItems = [
    {
      label: "Total Documents",
      value: getDisplayValue(stats?.total_documents),
      color: "from-green-400 to-emerald-600"
    },
    {
      label: "Recent (7d)",
      value: getDisplayValue(stats?.recent_docs_count),
      color: "from-blue-400 to-indigo-600"
    },
    {
      label: "Failed Uploads",
      value: getDisplayValue(stats?.failed_uploads),
      color: "from-orange-400 to-red-600"
    },
  ];

  return (
    <div className="flex flex-col gap-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-purple-900/50 via-blue-900/30 to-black border border-white/10 p-12 text-center md:text-left">
        <div className="absolute top-0 right-0 -mr-20 -mt-20 h-96 w-96 rounded-full bg-blue-500/20 blur-3xl"></div>
        <div className="absolute bottom-0 left-0 -ml-20 -mb-20 h-80 w-80 rounded-full bg-purple-500/20 blur-3xl"></div>

        <div className="relative z-10 max-w-2xl">
          <h1 className="text-5xl font-extrabold tracking-tight mb-6 bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            Your Knowledge Base, <br /> Supercharged.
          </h1>
          <p className="text-lg text-gray-400 mb-8 leading-relaxed">
            Manage your AI-curated summaries and deep dives.
            Sync securely between local storage and Google Drive.
          </p>
          <div className="flex gap-4 justify-center md:justify-start">
            <Link href="/documents" className="px-8 py-3 rounded-full bg-white text-black font-semibold hover:bg-gray-200 transition-colors shadow-lg shadow-white/10">
              Browse Documents
            </Link>
            <Link href="/settings" className="px-8 py-3 rounded-full bg-white/5 border border-white/10 text-white font-semibold hover:bg-white/10 transition-colors backdrop-blur-md">
              Configuration
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {statItems.map((stat, i) => (
          <div key={i} className="group relative overflow-hidden rounded-2xl bg-white/5 border border-white/10 p-6 hover:border-white/20 transition-all hover:shadow-2xl hover:shadow-purple-500/10">
            <div className={`absolute top-0 right-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-gradient-to-br ${stat.color} opacity-20 blur-2xl group-hover:opacity-30 transition-opacity`}></div>
            <h3 className="text-sm font-medium text-gray-400 mb-1">{stat.label}</h3>
            <p className="text-3xl font-bold text-white">{stat.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
