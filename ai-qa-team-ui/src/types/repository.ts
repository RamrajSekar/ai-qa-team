export type RepositorySource = "GITHUB_PUBLIC" | "LOCAL";

export interface RepositoryRecord {
  repository_id: string;
  project_id: string;
  source_type: RepositorySource;
  provider: "github" | "local";
  repository_url?: string | null;
  local_path?: string | null;
  branch: string;
  framework: string;
  source_commit_sha?: string | null;
  scan_status: "scanning" | "completed" | "failed" | "unsupported";
  scan_error?: string | null;
  test_count: number;
  last_scanned_at?: string | null;
}

export interface DiscoveredTest {
  test_id: string;
  repository_id: string;
  source_commit_sha: string;
  framework: string;
  test_name: string;
  relative_file_path: string;
  line_number?: number | null;
  tags: string[];
}
