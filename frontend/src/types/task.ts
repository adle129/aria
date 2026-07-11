export interface ArtifactsStatus {
  rfq_parsed: boolean;
  comparison_ready: boolean;
  proposal_ready: boolean;
  qa_ready: boolean;
  qa_excel_ready?: boolean;
  excel_ready: boolean;
}

export interface TaskSummary {
  task_id: string;
  file_name: string;
  status: string;
  processing_status: string;
  created_at?: string;
}

export interface SolutionDraftSection {
  function: string;
  module_key?: string;
  assumptions?: string;
  inputs?: string;
  work_content?: string;
  deliverables?: string;
  source_project?: string;
  deviation_rate?: string;
  similarity_score?: number;
}

export interface SolutionDraft {
  project_name?: string;
  sections: SolutionDraftSection[];
}

export interface QAItem {
  no: number;
  question: string;
  function: string;
  impact: string;
  history_reference?: string;
  /** @deprecated 兼容旧数据 */
  area?: string;
}

export interface TaskPayload {
  task_id: string;
  file_name?: string;
  processing_status: string;
  status: string;
  rfq_modules?: Record<string, unknown>;
  similar_projects?: Array<Record<string, unknown>>;
  comparison_table?: Record<string, unknown>;
  solution_draft?: SolutionDraft;
  qa_items?: QAItem[];
  artifacts_status?: ArtifactsStatus;
  qa_excel_ready?: boolean;
  excel_ready?: boolean;
  error_msg?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ManpowerBreakdownItem {
  deliverable: string;
  function: string;
  man_days: number;
  source: string;
}
