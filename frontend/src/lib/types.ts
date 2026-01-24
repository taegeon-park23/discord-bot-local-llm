export enum DocType {
    SUMMARY = "SUMMARY",
    DEEP_DIVE = "DEEP_DIVE",
    WEEKLY_REPORT = "WEEKLY_REPORT",
    OTHER = "OTHER",
}

export enum UploadStatus {
    PENDING = "PENDING",
    SUCCESS = "SUCCESS",
    FAILED = "FAILED",
}

export interface Document {
    id: number;
    title: string;
    source_url?: string;
    doc_type: DocType;
    local_file_path: string;
    gdrive_file_id?: string;
    gdrive_upload_status: UploadStatus;
    created_at: string;
    updated_at: string;
    last_synced_at?: string;
    tags: string[];
    category?: string;
}

export interface DashboardStats {
    total_documents: number;
    failed_uploads: number;
    recent_docs_count: number;
}

export interface SearchResultItem {
    chunk_id: number;
    document_id: number;
    document_title: string;
    content: string;
    score: string;
}
