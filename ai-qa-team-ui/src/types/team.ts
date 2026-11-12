export type ProjectRole = "ADMIN" | "TESTER";

export interface ProjectMembership {
  membership_id: string;
  project_id: string;
  user_id?: string | null;
  email: string;
  name?: string | null;
  role: ProjectRole;
  status: "INVITED" | "ACTIVE" | "LEGACY_REVIEW_REQUIRED";
  invited_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectTeam {
  current_user_role: ProjectRole;
  members: ProjectMembership[];
}
