'use client';
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { MoreHorizontal, Plus, ArrowUpRight, History, Globe, Pencil } from 'lucide-react';
import dynamic from "next/dynamic";
import PendingReviews from '@/components/projects/PendingReviews';
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui/dropdown-menu';
import { apiFetch } from '@/utils/api';

const EnvironmentModal = dynamic(() => import('@/components/environment/EnvironmentModal'), {ssr:false});
const EditProjectModal = dynamic(() => import('@/components/projects/EditProjectModal'), {ssr:false});
const DeleteProjectModal = dynamic(() => import('@/components/projects/DeleteProjectModal'), {ssr:false});

// ---------------------- Types ----------------------
interface Project {
  display_id?: string | null;
  id: string;
  project_id: string;
  name: string;
  description?: string;
  created_by: string;
  created_at: string;
  agent_identities: Record<string, string>;
  current_user_role?: "ADMIN" | "TESTER";
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
  const automationEnabled = enabled("automation_execution_ui");
  const storiesEnabled = enabled("story_management");
  const scenariosEnabled = storiesEnabled && enabled("scenario_generation");
  const testsEnabled = enabled("test_generation");
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [loading, setLoading] = useState(true);
  const [detailStates,setDetailStates]=useState({stories:"loading",testcases:"loading",environments:"loading"});
  const [project, setProject] = useState<Project | null>(null);
  const [editingName, setEditingName] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [savingName, setSavingName] = useState(false);
  const [nameError, setNameError] = useState('');
  const nameSavePending = useRef(false);
  const nameEditCancelled = useRef(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [scenarioTotal, setScenarioTotal] = useState<number | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioError, setScenarioError] = useState(false);
  const pendingLoad = useRef<AbortController | null>(null);

  const [openEnvironmentModal, setOpenEnvironmentModal] = useState(false);
  const [openEditModal, setOpenEditModal] = useState(false);
  const [openDeleteModal, setOpenDeleteModal] = useState(false);

  const [stories, setStories] = useState<Story[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [testcases, setTestcases] = useState<Testcase[]>([]);
  const [environments, setEnvironments] = useState<Env[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);

  const loadAll = useCallback(async () => {
    pendingLoad.current?.abort();
    const controller = new AbortController();
    pendingLoad.current = controller;
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]);
    const scopedProject = encodeURIComponent(projectId);
    const get = (path: string) => apiFetch(path, { signal });
    const emptyList = { data: [],ok:true };

    setLoading(true);
    setLoadError(null);
    setHistoryError(false);
    setHistoryLoading(true);
    setScenarioTotal(null);
    setScenarioError(false);
    setScenarioLoading(scenariosEnabled);
    setScenarios([]);

    if (automationEnabled) void get('/execute?skip=0&limit=200').then(result => {
      if (!result.ok || !Array.isArray(result.data)) throw new Error('HISTORY_UNAVAILABLE');
      if (!controller.signal.aborted) setExecutions(result.data.filter((item: Execution) => item.project_id === projectId));
    }).catch(() => {
      if (!controller.signal.aborted) { setExecutions([]); setHistoryError(true); }
    }).finally(() => {
      if (!controller.signal.aborted) setHistoryLoading(false);
    });

    if (scenariosEnabled) {
      void get(`/scenarios/project-overview?project_id=${scopedProject}`).then(result => {
        if (!result.ok || !Array.isArray(result.data?.recent) || typeof result.data?.total !== 'number') {
          throw new Error('SCENARIOS_UNAVAILABLE');
        }
        if (!controller.signal.aborted) {
          setScenarios(result.data.recent);
          setScenarioTotal(result.data.total);
        }
      }).catch(() => {
        if (!controller.signal.aborted) setScenarioError(true);
      }).finally(() => {
        if (!controller.signal.aborted) setScenarioLoading(false);
      });
    }

    setDetailStates({stories:"loading",testcases:"loading",environments:"loading"});
    const summary=async(key:"stories"|"testcases"|"environments",path:string,active:boolean)=>{
      try{
        const response=active?await get(path):emptyList;
        if(!response.ok||!Array.isArray(response.data))throw new Error("SUMMARY_UNAVAILABLE");
        if(controller.signal.aborted)return;
        if(key==="stories")setStories(response.data);else if(key==="testcases")setTestcases(response.data);else setEnvironments(response.data);
        setDetailStates(previous=>({...previous,[key]:"ready"}));
      }catch{if(!controller.signal.aborted)setDetailStates(previous=>({...previous,[key]:"unavailable"}));}
    };
    const details=Promise.all([
      summary("stories",`/stories?project_id=${scopedProject}&skip=0&limit=100`,storiesEnabled),
      summary("testcases",`/testcases/testcases?project_id=${scopedProject}`,testsEnabled),
      summary("environments",`/environments?project_id=${scopedProject}`,true),
    ]);
    try {
      const p=await get(`/projects/${scopedProject}`);
      if(!p.ok)throw new Error('PROJECT_UNAVAILABLE');
      if(!controller.signal.aborted)setProject(p.data);
    }catch{
      if(!controller.signal.aborted)setLoadError('Unable to load project details. Check your connection and try again.');
    }finally{
      if(!controller.signal.aborted)setLoading(false);
    }
    await details;
  }, [projectId, storiesEnabled, scenariosEnabled, testsEnabled, automationEnabled]);

  useEffect(() => {
    if (ready) void loadAll();
    return () => pendingLoad.current?.abort();
  }, [ready, loadAll]);

  if (!loading && loadError) {
    return <div className="p-6" role="alert"><p>{loadError}</p><button className="workspace-button" onClick={loadAll}>Try again</button></div>;
  }

  if (loading || !project) {
    return (
      <div className="p-6 animate-pulse">
        <div className="h-6 bg-gray-200 w-48 rounded mb-2"></div>
        <div className="h-4 bg-gray-200 w-72 rounded"></div>
      </div>
    );
  }

  const canManage = project.current_user_role === "ADMIN";
  async function saveProjectName() {
    if (nameSavePending.current || nameEditCancelled.current) return;
    const value = projectName.trim();
    if (!value) { setNameError('Enter a project name.'); return; }
    if (value === project!.name) { setEditingName(false); return; }
    nameSavePending.current = true; setSavingName(true); setNameError('');
    try {
      const response = await apiFetch(`/projects/${encodeURIComponent(projectId)}`, {method:'PATCH',body:JSON.stringify({name:value})});
      if (!response.ok) throw new Error(typeof response.data?.detail === 'string' ? response.data.detail : 'Could not save project name.');
      setProject(current => current?.project_id === projectId ? {...current,name:value} : current);
      setEditingName(false);
      window.dispatchEvent(new Event('projects-updated'));
    } catch (failure) { setNameError(failure instanceof Error ? failure.message : 'Could not save project name.'); }
    finally { nameSavePending.current = false; setSavingName(false); }
  }
  return (
    <div>
      <div className="workspace-page-header">
        <div>
          <p className="workspace-eyebrow">Project overview</p>
          <div className="workspace-name-row">
            {editingName ? <input className="project-name-input" aria-label="Project name" autoFocus value={projectName} disabled={savingName}
              onChange={event=>setProjectName(event.target.value)} onBlur={()=>void saveProjectName()}
              onKeyDown={event=>{if(event.key==='Enter'){event.preventDefault();event.currentTarget.blur();}if(event.key==='Escape'){event.preventDefault();nameEditCancelled.current=true;setEditingName(false);setNameError('');}}} /> : <>
              <h1>{project.name}</h1>
              {canManage && <button type="button" className="workspace-name-pencil" aria-label="Edit project name" title="Edit project name" onClick={()=>{nameEditCancelled.current=false;setProjectName(project.name);setNameError('');setEditingName(true);}}><Pencil size={16} aria-hidden="true" /></button>}
            </>}
          </div>
          {savingName && <p role="status" className="workspace-metadata">Saving...</p>}
          {nameError && <p role="alert">{nameError}</p>}
          <p className="workspace-description">{project.description || "Manage your environments and review your execution history."}</p>
          <p className="workspace-metadata">{project.display_id || project.project_id} · Created {new Date(project.created_at).toLocaleDateString()}</p>
        </div>
        {canManage && <div className="workspace-actions">
          <DropdownMenu>
            <DropdownMenuTrigger asChild><button className="workspace-button" aria-label="Project actions"><MoreHorizontal size={18} /></button></DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => setOpenEditModal(true)}>Edit project details</DropdownMenuItem>
              <DropdownMenuItem variant="destructive" onSelect={() => setOpenDeleteModal(true)} aria-label="Delete project">Delete</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>}
      </div>
      <div className="workspace-metrics">
        <KpiCard label="Environments" value={detailStates.environments!=="ready"?"—":environments.length} />
        {automationEnabled && <KpiCard label="Recorded executions" value={historyLoading || historyError ? '—' : executions.length} />}
        {storiesEnabled && <KpiCard label="Stories" value={detailStates.stories!=="ready"?"—":stories.length} />}
        {scenariosEnabled && <KpiCard label="Scenarios" value={scenarioTotal ?? '—'} />}
        {testsEnabled && <KpiCard label="Testcases" value={detailStates.testcases!=="ready"?"—":testcases.length} />}
      </div>
      <section className="workspace-panel" aria-labelledby="environment-title">
        <div className="workspace-panel-header">
          <h2 id="environment-title">Environments</h2>
          {canManage && <button className="workspace-button workspace-primary" onClick={() => setOpenEnvironmentModal(true)}><Plus size={15} />Add environment</button>}
        </div>
        {detailStates.environments==="loading"?<p role="status">Loading environments…</p>:detailStates.environments==="unavailable"?<p>Project summaries unavailable. Reload to try again.</p>:environments.length ? <div className="workspace-panel-body">
          {environments.map((env) => <div className="workspace-row" key={env.env_id || env.id}><Link className="workspace-summary-link min-w-0" href={`/projects/${projectId}/environments`}>
            <div className="workspace-row-title">{env.name || env.env_type?.toUpperCase() || "Environment"}</div><div className="workspace-row-subtitle">{env.base_url || env.url || env.env_id}</div></Link>
            <span className="workspace-badge">{env.env_type}</span><ArrowUpRight size={16} aria-hidden="true" />
          </div>)}
        </div> : <div className="workspace-empty"><Globe size={24} /><strong>No environments configured</strong>{canManage ? "Add your first environment to keep project settings in one place." : "A Project Admin can add an environment."}</div>}
      </section>
      {canManage && openEnvironmentModal && <EnvironmentModal open={openEnvironmentModal} onClose={() => setOpenEnvironmentModal(false)} mode="create" projectId={projectId} onSaved={loadAll} />}
      {automationEnabled && <section id="execution-history" className="workspace-panel" aria-labelledby="history-title">
        <div className="workspace-panel-header"><h2 id="history-title">Execution history</h2><Link href={`/projects/${projectId}/execution-history`}>View history →</Link>{!historyError && !historyLoading && <span className="workspace-badge">{executions.length} recorded</span>}</div>
        {historyLoading ? <p className="workspace-empty" role="status">Loading execution history…</p>
          : historyError ? <div className="workspace-empty" role="alert"><strong>Execution history unavailable</strong>Project details are available. Check your connection and try again.<button className="workspace-button" onClick={loadAll}>Try again</button></div> : executions.length ? <div className="workspace-panel-body">
          {executions.map((execution) => <div key={execution.execution_id} className="workspace-row"><div><div className="workspace-row-title">Execution #{execution.execution_id}</div><div className="workspace-row-subtitle">{execution.started_at ? new Date(execution.started_at).toLocaleString() : "No start time recorded"}</div></div><span className="workspace-badge">{execution.status}</span></div>)}
        </div> : <div className="workspace-empty"><History size={24} /><strong>No execution history yet</strong>Recorded results for this project will appear here.</div>}
      </section>}

      {/* --- Modals --- */}

      {canManage && openEditModal && <EditProjectModal
        open={openEditModal}
        onClose={() => setOpenEditModal(false)}
        project={project}
        onUpdated={loadAll}
      />}


      {canManage && openDeleteModal && <DeleteProjectModal
        open={openDeleteModal}
        onClose={() => setOpenDeleteModal(false)}
        projectId={project.project_id}
        projectName={project.name}
        onDeleted={() => router.push('/projects')}
      />}

      <PendingReviews key={projectId} projectId={projectId} />

      {/* SECTIONS */}
      {storiesEnabled && <Section
        title="Recent Stories"
        emptyText={detailStates.stories==="loading"?"Loading stories…":detailStates.stories==="unavailable"?"Story summary unavailable.":"No items yet."}
        viewAllHref={`/projects/${projectId}/stories`}
        items={stories}
        maxItems={5}
        renderItem={(s: Story) => (
          <MiniCard
            title={s.title}
            subtitle={s.description}
            onClick={() => router.push(`/projects/${projectId}/stories/${s.story_id}`)}
          />
        )}
      />}

      {scenariosEnabled && <Section
        title="Recent Scenarios"
        viewAllHref={`/projects/${projectId}/stories`}
        viewAllLabel="Open stories →"
        items={scenarios}
        emptyText={scenarioLoading ? 'Loading scenarios…' : scenarioError ? 'Scenario summary unavailable.' : 'No items yet.'}
        maxItems={5}
        renderItem={(s: Scenario) => (
          <MiniCard
            title={s.title}
            subtitle={`${s.complexity} • ${s.approved ? 'Approved' : 'Pending'}`}
            onClick={() => router.push(`/projects/${projectId}/stories/${s.story_id}`)}
          />
        )}
      />}

      {testsEnabled && <Section
        title="Recent Testcases"
        emptyText={detailStates.testcases==="loading"?"Loading test cases…":detailStates.testcases==="unavailable"?"Test case summary unavailable.":"No items yet."}
        viewAllHref={scenariosEnabled ? `/projects/${projectId}/stories` : undefined}
        viewAllLabel="Generate from a story →"
        items={testcases}
        maxItems={5}
        renderItem={(t: Testcase) => (
          <MiniCard
            title={t.title}
            subtitle={t.complexity}
          />
        )}
      />}


    </div>
  );
}

// ---------------------- COMPONENTS ----------------------

function KpiCard({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="workspace-metric">
      <div className="workspace-metric-label">{label}</div>
      <div className="workspace-metric-value">{value}</div>
    </div>
  );
}

function Section<T>({ title, viewAllHref, viewAllLabel = 'View all →', items, maxItems, renderItem, emptyText = 'No items yet.' }: { title: string; viewAllHref?: string; viewAllLabel?: string; items: T[]; maxItems: number; renderItem: (item: T) => ReactNode; emptyText?: string }) {
  return (
    <div className="bg-white border rounded-xl shadow-sm p-4 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-semibold">{title}</h2>
        {viewAllHref && <Link href={viewAllHref} className="text-xs text-blue-600 hover:underline">
          {viewAllLabel}
        </Link>}
      </div>

      {items.length === 0 ? (
        <p className="text-xs text-gray-500">{emptyText}</p>
      ) : (
        <div className="space-y-2">
          {items.slice(0, maxItems).map((item, idx) => (
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
