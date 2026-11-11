"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function ExecutionTrendChart({ data }: { data: any[] }) {
  return (
    <div className="border p-4 rounded-lg bg-white shadow h-64">
      <h3 className="font-semibold mb-2">Execution Trend</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Line type="monotone" dataKey="passed" stroke="#22c55e" strokeWidth={2} />
          <Line type="monotone" dataKey="failed" stroke="#ef4444" strokeWidth={2} />
          <Line type="monotone" dataKey="total" stroke="#6366f1" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}


// "use client";

// import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// const dummyData = [
//   { date: "Mon", count: 4 },
//   { date: "Tue", count: 7 },
//   { date: "Wed", count: 3 },
//   { date: "Thu", count: 9 },
//   { date: "Fri", count: 6 },
// ];

// export default function ExecutionTrendChart() {
//   return (
//     <ResponsiveContainer width="100%" height={220}>
//       <LineChart data={dummyData}>
//         <XAxis dataKey="date" />
//         <YAxis />
//         <Tooltip />
//         <Line type="monotone" dataKey="count" stroke="#7C3AED" strokeWidth={2} />
//       </LineChart>
//     </ResponsiveContainer>
//   );
// }

