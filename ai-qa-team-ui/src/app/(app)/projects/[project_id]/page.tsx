'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
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
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<Project | null>(null);

  const [openEditModal, setOpenEditModal] = useState(false);
  const [openAgentModal, setOpenAgentModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);

  const [stories, setStories] = useState<Story[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [testcases, setTestcases] = useState<Testcase[]>([]);
  const [environments, setEnvironments] = useState<Env[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);

  useEffect(() => {
    loadAll();
  }, [projectId]);

  async function loadAll() {
    try {
      setLoading(true);

      // 1. Project
      const p = await apiFetch(`/projects/${projectId}`);
      const project = p.data;

      // 2. Stories
      const s = await apiFetch(`/stories?skip=0&limit=100`);
      const storyList: Story[] = Array.isArray(s.data) ? s.data : [];
      const projectStories = storyList.filter((x) => x.project_id === projectId);

      // 3. Scenarios
      const allSc: Scenario[] = [];
      for (const story of projectStories) {
        const scRes = await apiFetch(`/scenarios?story_id=${story.story_id}`);
        const scList: Scenario[] = Array.isArray(scRes.data) ? scRes.data : [];
        allSc.push(...scList);
      }

      // 4. Testcases
      const tcRes = await apiFetch(`/testcases/testcases?project_id=${projectId}`);
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
    <div className="p-6 space-y-8">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center">
        <div>
          <h1 className="text-2xl font-semibold">{project.name}</h1>
          <p className="text-gray-500 text-sm">{project.description}</p>
          <p className="text-xs text-gray-400 mt-1">
            {project.project_id} • Created {new Date(project.created_at).toLocaleString()} by{' '}
            {project.created_by}
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button onClick={() => setOpenEditModal(true)} className="px-4 py-2 border rounded-md">
          Edit Project
        </button>

        <button onClick={() => setOpenAgentModal(true)} className="px-4 py-2 border rounded-md">
          Agent Settings
        </button>

        <button
          onClick={() => setOpenDeleteModal(true)}
          className="px-4 py-2 border border-red-500 text-red-500 rounded-md"
        >
          Delete
        </button>
      </div>

      {/* KPI CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard label="Stories" value={stories.length} />
        <KpiCard label="Scenarios" value={scenarios.length} />
        <KpiCard label="Testcases" value={testcases.length} />
        <KpiCard label="Environments" value={environments.length} />
        <KpiCard label="Executions" value={executions.length} />
      </div>

      {/* --- Modals --- */}

      <EditProjectModal
        open={openEditModal}
        onClose={() => setOpenEditModal(false)}
        project={project}
        onUpdated={loadAll}
      />

      <AgentSettingsModal
        open={openAgentModal}
        onClose={() => setOpenAgentModal(false)}
        projectId={project.project_id}
        initialAgents={project.agent_identities}
        onUpdated={loadAll}
      />

      <DeleteProjectModal
        open={openDeleteModal}
        onClose={() => setOpenDeleteModal(false)}
        projectId={project.project_id}
        projectName={project.name}
        onDeleted={() => router.push('/projects')}
      />

      {/* SECTIONS */}
      <Section
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
      />

      <Section
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
      />

      <Section
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
      />

      <Section
        title="Recent Executions"
        viewAllHref="/executions"
        items={executions}
        maxItems={5}
        renderItem={(ex: Execution) => (
          <MiniCard
            title={`Execution #${ex.execution_id}`}
            subtitle={ex.status}
            onClick={() => router.push(`/executions/${ex.execution_id}`)}
          />
        )}
      />

      <Section
        title="Environments"
        viewAllHref="/environments"
        items={environments}
        maxItems={5}
        renderItem={(env: Env) => (
          <MiniCard
            title={env.name}
            subtitle={env.env_type}
            onClick={() => router.push(`/environments/${env.id}`)}
          />
        )}
      />
    </div>
  );
}

// ---------------------- COMPONENTS ----------------------

function KpiCard({ label, value }: { label: string; value: any }) {
  return (
    <div className="p-4 bg-white border rounded-xl shadow-sm">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
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
