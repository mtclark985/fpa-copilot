import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Line,
  ComposedChart,
} from "recharts";
import { apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { DashboardKPIs } from "@/types/api";

function KpiCard({
  label,
  value,
  subtext,
}: {
  label: string;
  value: string;
  subtext?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        {label}
      </p>
      <p className="text-2xl font-semibold mt-1">{value}</p>
      {subtext && (
        <p className="text-xs text-muted-foreground mt-1">{subtext}</p>
      )}
    </div>
  );
}

const severityColors: Record<string, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-kpis"],
    queryFn: () => apiFetch<DashboardKPIs>("/kpis/dashboard"),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading dashboard...
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex items-center justify-center h-64 text-destructive">
        Failed to load dashboard data. Is the backend running?
      </div>
    );
  }

  const chartData = data.monthly_data.map((d) => ({
    ...d,
    variance: d.actual - d.forecast,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Current month: {data.current_month}
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Current Month" value={data.current_month} />
        <KpiCard
          label="Headcount EOP"
          value={data.headcount_eop.toLocaleString()}
        />
        <KpiCard
          label="YTD Comp Actuals"
          value={formatCurrency(data.ytd_actuals)}
        />
        <KpiCard
          label="YTD Variance to Plan"
          value={formatCurrency(data.ytd_variance)}
          subtext={data.ytd_variance > 0 ? "Over plan" : "Under plan"}
        />
      </div>

      {/* Forecast FY Landing + Active Forecast Info */}
      <div className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Forecasted FY Landing
            </p>
            <p className="text-2xl font-semibold mt-1">
              {formatCurrency(data.fy_forecast)}
            </p>
          </div>
          {data.active_forecast && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">
                Active Forecast: {data.active_forecast.name}
              </p>
              <p className="text-xs text-muted-foreground">
                Source: {data.active_forecast.source?.replace(/_/g, " ")}
                {data.active_forecast.created_at && (
                  <> | Updated {new Date(data.active_forecast.created_at).toLocaleDateString()}</>
                )}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Pending Proposals Banner */}
      {data.pending_proposals > 0 && (
        <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4 flex items-center justify-between">
          <p className="text-sm text-yellow-800">
            {data.pending_proposals} proposal{data.pending_proposals > 1 ? "s" : ""} awaiting your review
          </p>
          <a
            href="/proposals"
            className="px-3 py-1.5 text-sm rounded-md bg-yellow-600 text-white hover:bg-yellow-700 transition-colors"
          >
            Review Proposals
          </a>
        </div>
      )}

      {/* Chart: Actual vs Forecast */}
      <div className="rounded-lg border border-border bg-card p-5">
        <h3 className="text-sm font-medium text-muted-foreground mb-4">
          Monthly Actual vs. Forecast Comp Expense
        </h3>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="period" tick={{ fontSize: 12 }} />
            <YAxis
              tickFormatter={(v: number) => `$${(v / 1_000_000).toFixed(1)}M`}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              formatter={(value: number) => formatCurrency(value)}
              labelStyle={{ fontWeight: 600 }}
            />
            <Legend />
            <Bar
              dataKey="actual"
              name="Actual"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
            />
            <Line
              dataKey="forecast"
              name="Forecast"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={{ fill: "#f59e0b", r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Recent Agent Activity */}
      <div className="rounded-lg border border-border bg-card p-5">
        <h3 className="text-sm font-medium text-muted-foreground mb-4">
          Recent Agent Activity
        </h3>
        {data.recent_assessments.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No agent assessments yet. Run variance analysis to see results here.
          </p>
        ) : (
          <div className="space-y-3">
            {data.recent_assessments.map((a) => (
              <div
                key={a.id}
                className="flex items-start gap-3 text-sm border-b border-border pb-3 last:border-0"
              >
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${severityColors[a.severity ?? "low"]}`}
                >
                  {a.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">
                    {a.period} &middot; {a.category}
                  </p>
                  <p className="text-muted-foreground truncate">
                    {a.rationale}
                  </p>
                </div>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {a.suggested_action}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
