export default function DashboardHome() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Welcome back 👋</h2>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="qs-card">Projects: 1</div>
        <div className="qs-card">Executions this month: 20</div>
        <div className="qs-card">AI Generations left: 3</div>
      </div>
    </div>
  );
}
