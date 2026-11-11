export interface Recording {
  id: string;
  recording_id: string;
  story_id: string;
  project_id?: string;
  steps: any[];
  notes?: string;
  agent_name?: string;
  is_editable: boolean;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  updated_by: string;
}

