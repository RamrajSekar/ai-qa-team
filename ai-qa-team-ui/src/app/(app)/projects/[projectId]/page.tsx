'use client';
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { MoreHorizontal, Plus, ArrowUpRight, History, Globe } from 'lucide-react';
import EnvironmentModal from '@/components/environment/EnvironmentModal';
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui/dropdown-menu';
import { apiFetch } from '@/utils/api';
import EditProjectModal from '@/components/projects/EditProjectModal';
import AgentSettingsModal from '@/components/projects/AgentSettingsModal';
import DeleteProjectModal from '@/components/projects/DeleteProjectModal';

// ---------------------- Types ----------------------
interface Project {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  created_by: string;
  created_at: string;
  agent_identities: Record<string, any>;
}

interface Story {
  story_id: string;
  project_id: string;
  title: string;
  description: string;
  created_at: string;
}

interface Scenario {
  scenario_id: string;
  story_id: string;
  project_id: string;
  title: string;
  created_at: string;
  complexity: string;
  approved: boolean;
}

interface Testcase {
  testcase_id: string;
  project_id: string;
  title: string;
  complexity: string;
  created_at: string;
}

interface Env {
  id: string;
  project_id: string;
  name: string;
  env_type: string;
  created_at: string;
  url: string;
  base_url?: string;
  env_id?: string;
}

interface Execution {
  execution_id: string;
  project_id: string;
  testcase_id: string;
  status: string;
  triggered_by: string;
  started_at?: string;
}

// ---------------------- Page ----------------------

export default function ProjectPage() {
  const { enabled, ready } = useFeatures();
  const storiesEnabled = enabled("story_management");
  const scenariosEnabled = storiesEnabled && enabled("scenario_generation");
  const testsEnabled = enabled("test_generation");
  const agentsEnabled = enabled("recorder") || enabled("scenario_generation") || enabled("test_generation") || enabled("native_execution");
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<Project | null>(null);

  const [openEnvironmentModal, setOpenEnvironmentModal] = useState(false);
  const [openEditModal, setOpenEditModal] = useState(false);
  const [openAgentModal, setOpenAgentModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);

  const [stories, setStories] = useState<Story[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [testcases, setTestcases] = useState<Testcase[]>([]);
  const [environments, setEnvironments] = useState<Env[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);

  useEffect(() => {
    if (ready) loadAll();
  }, [projectId, ready, storiesEnabled, scenariosEnabled, testsEnabled]);

  async function loadAll() {
    try {
      setLoading(true);

      // 1. Project
      const p = await apiFetch(`/projects/${projectId}`);
      const project = p.data;

      // 2. Stories
      const s = storiesEnabled ? await apiFetch(`/stories?project_id=${projectId}&skip=0&limit=100`) : { data: [] };
      const storyList: Story[] = Array.isArray(s.data) ? s.data : [];
      const projectStories = storyList.filter((x) => x.project_id === projectId);

      // 3. Scenarios
      const allSc: Scenario[] = [];
      for (const story of (scenariosEnabled ? projectStories : [])) {
        const scRes = await apiFetch(`/scenarios?story_id=${story.story_id}`);
        const scList: Scenario[] = Array.isArray(scRes.data) ? scRes.data : [];
        allSc.push(...scList);
      }

      // 4. Testcases
      const tcRes = testsEnabled ? await apiFetch(`/testcases/testcases?project_id=${projectId}`) : { data: [] };
      const tcList: Testcase[] = Array.isArray(tcRes.data) ? tcRes.data : [];

      // 5. Environments
      const envRes = await apiFetch(`/environments?project_id=${projectId}`);
      const envList: Env[] = Array.isArray(envRes.data) ? envRes.data : [];

      // 6. Executions
      const execRes = await apiFetch(`/execute?skip=0&limit=200`);
      const execList: Execution[] = Array.isArray(execRes.data) ? execRes.data : [];
      const execFiltered = execList.filter((e) => e.project_id === projectId);

      // Set state
      setProject(project);
      setStories(projectStories);
      setScenarios(allSc);
      setTestcases(tcList);
      setEnvironments(envList);
      setExecutions(execFiltered);
    } finally {
      setLoading(false);
    }
  }

  if (loading || !project) {
    return (
      <div className="p-6 animate-pulse">
        <div className="h-6 bg-gray-200 w-48 rounded mb-2"></div>
        <div className="h-4 bg-gray-200 w-72 rounded"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="workspace-page-header">
        <div>
          <p className="workspace-eyebrow">Project overview</p>
          <h1>{project.name}</h1>
          <p className="workspace-description">{project.description || "Manage your environments and review your execution history."}</p>
          <p className="workspace-metadata">{project.project_id} · Created {new Date(project.created_at).toLocaleDateString()}</p>
        </div>
        <div className="workspace-actions">
          <button onClick={() => setOpenEditModal(true)} className="workspace-button">Edit Project</button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild><button className="workspace-button" aria-label="Project actions"><MoreHorizontal size={18} /></button></DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {agentsEnabled && <DropdownMenuItem onSelect={() => setOpenAgentModal(true)}>Agent Settings</DropdownMenuItem>}
              <DropdownMenuItem variant="destructive" onSelect={() => setOpenDeleteModal(true)}>Delete project</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      <div className="workspace-metrics">
        <KpiCard label="Environments" value={environments.length} />
        <KpiCard label="Recorded executions" value={executions.length} />
        {storiesEnabled && <KpiCard label="Stories" value={stories.length} />}
        {scenariosEnabled && <KpiCard label="Scenarios" value={scenarios.length} />}
        {testsEnabled && <KpiCard label="Testcases" value={testcases.length} />}
      </div>
      <section className="workspace-panel" aria-labelledby="environment-title">
        <div className="workspace-panel-header">
          <h2 id="environment-title">Environments</h2>
          <button className="workspace-button workspace-primary" onClick={() => setOpenEnvironmentModal(true)}><Plus size={15} />Add environment</button>
        </div>
        {environments.length ? <div className="workspace-panel-body">
          {environments.map((env) => <Link className="workspace-row" key={env.env_id || env.id} href={`/projects/${projectId}/environments`}>
            <div><div className="workspace-row-title">{env.name || env.env_type?.toUpperCase() || "Environment"}</div><div className="workspace-row-subtitle">{env.base_url || env.url || env.env_id}</div></div>
            <span className="workspace-badge">{env.env_type}</span><ArrowUpRight size={16} aria-hidden="true" />
          </Link>)}
        </div> : <div className="workspace-empty"><Globe size={24} /><strong>No environments configured</strong>Add your first environment to keep project settings in one place.</div>}
      </section>
      <EnvironmentModal open={openEnvironmentModal} onClose={() => setOpenEnvironmentModal(false)} mode="create" projectId={projectId} onSaved={loadAll} />
      <section id="execution-history" className="workspace-panel" aria-labelledby="history-title">
        <div className="workspace-panel-header"><h2 id="history-title">Execution history</h2><span className="workspace-badge">{executions.length} recorded</span></div>
        {executions.length ? <div className="workspace-panel-body">
          {executions.map((execution) => <div key={execution.execution_id} className="workspace-row"><div><div className="workspace-row-title">Execution #{execution.execution_id}</div><div className="workspace-row-subtitle">{execution.started_at ? new Date(execution.started_at).toLocaleString() : "No start time recorded"}</div></div><span className="workspace-badge">{execution.status}</span></div>)}
        </div> : <div className="workspace-empty"><History size={24} /><strong>No execution history yet</strong>Recorded results for this project will appear here.</div>}
      </section>

      {/* --- Modals --- */}

      <EditProjectModal
        open={openEditModal}
        onClose={() => setOpenEditModal(false)}
        project={project}
        onUpdated={loadAll}
      />

      {agentsEnabled && <AgentSettingsModal
        open={openAgentModal}
        onClose={() => setOpenAgentModal(false)}
        projectId={project.project_id}
        initialAgents={project.agent_identities}
        onUpdated={loadAll}
      />}

      <DeleteProjectModal
        open={openDeleteModal}
        onClose={() => setOpenDeleteModal(false)}
        projectId={project.project_id}
        projectName={project.name}
        onDeleted={() => router.push('/projects')}
      />

      {/* SECTIONS */}
      {storiesEnabled && <Section
        title="Recent Stories"
        viewAllHref="/stories"
        items={stories}
        maxItems={5}
        renderItem={(s: Story) => (
          <MiniCard
            title={s.title}
            subtitle={s.description}
            onClick={() => router.push(`/stories/${s.story_id}`)}
          />
        )}
      />}

      {scenariosEnabled && <Section
        title="Recent Scenarios"
        viewAllHref="/scenarios"
        items={scenarios}
        maxItems={5}
        renderItem={(s: Scenario) => (
          <MiniCard
            title={s.title}
            subtitle={`${s.complexity} • ${s.approved ? 'Approved' : 'Pending'}`}
            onClick={() => router.push(`/scenarios/${s.scenario_id}`)}
          />
        )}
      />}

      {testsEnabled && <Section
        title="Recent Testcases"
        viewAllHref="/testcases"
        items={testcases}
        maxItems={5}
        renderItem={(t: Testcase) => (
          <MiniCard
            title={t.title}
            subtitle={t.complexity}
            onClick={() => router.push(`/testcases/${t.testcase_id}`)}
          />
        )}
      />}

    </div>
  );
}

// ---------------------- COMPONENTS ----------------------

function KpiCard({ label, value }: { label: string; value: any }) {
  return (
    <div className="workspace-metric">
      <div className="workspace-metric-label">{label}</div>
      <div className="workspace-metric-value">{value}</div>
    </div>
  );
}

function Section({ title, viewAllHref, items, maxItems, renderItem }: any) {
  return (
    <div className="bg-white border rounded-xl shadow-sm p-4 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-semibold">{title}</h2>
        <Link href={viewAllHref} className="text-xs text-blue-600 hover:underline">
          View all →
        </Link>
      </div>

      {items.length === 0 ? (
        <p className="text-xs text-gray-500">No items yet.</p>
      ) : (
        <div className="space-y-2">
          {items.slice(0, maxItems).map((item: any, idx: number) => (
            <div key={idx}>{renderItem(item)}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function MiniCard({
  title,
  subtitle,
  onClick,
}: {
  title: string;
  subtitle?: string;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className="border rounded-lg p-3 cursor-pointer hover:bg-gray-50 shadow-sm"
    >
      <div className="font-medium text-sm">{title}</div>
      <div className="text-xs text-gray-500">{subtitle}</div>
    </div>
  );
}
