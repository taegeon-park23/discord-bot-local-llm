import { Document } from "./types";

const API_Base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDocuments(skip = 0, limit = 50): Promise<Document[]> {
    const res = await fetch(`${API_Base}/api/documents?skip=${skip}&limit=${limit}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to fetch documents");
    return res.json();
}

export async function fetchDocument(id: number): Promise<Document> {
    const res = await fetch(`${API_Base}/api/documents/${id}`);
    if (!res.ok) throw new Error("Failed to fetch document");
    return res.json();
}

export async function fetchDocumentContent(id: number): Promise<{ content: string }> {
    const res = await fetch(`${API_Base}/api/documents/${id}/content`);
    if (!res.ok) throw new Error("Failed to fetch document content");
    return res.json();
}

export async function updateDocumentContent(id: number, content: string): Promise<void> {
    const res = await fetch(`${API_Base}/api/documents/${id}/content`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
    });
    if (!res.ok) throw new Error("Failed to update content");
}

export async function retryUpload(id: number): Promise<void> {
    const res = await fetch(`${API_Base}/api/documents/${id}/retry`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to retry upload");
}
