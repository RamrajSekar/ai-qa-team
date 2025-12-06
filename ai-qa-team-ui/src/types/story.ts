export interface Story {
  id: string;
  story_id: string;
  project_id: string;
  title: string;
  description?: string;
  acceptance_criteria?: string;
  out_of_scope?: string;
  created_at: string;
  recording_id?: string | null;
}
