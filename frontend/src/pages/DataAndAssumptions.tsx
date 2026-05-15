import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { CostCenter } from "@/types/api";

// Tab types
const tabs = ["Company", "Hiring Plan", "Forecast Assumptions", "Simulator Events"] as const;
type Tab = (typeof tabs)[number];

// API response types
interface TransparencyEmployee {
  id: number;
  employee_number: string;
  name: string;
  cost_center_id: number;
  cost_center_name: string;
  cost_center_code: string;
  job_level: string;
  location: string;
  hire_date: string;
  base_salary: number;
  bonus_target_pct: number;
  status: string;
  termination_date: string | null;
}

interface EmployeesResponse {
  total: number;
  page: number;
  page_size: number;
  employees: TransparencyEmployee[];
}

interface OpenPosition {
  id: number;
  cost_center_name: string;
  cost_center_code: string;
  job_level: string;
  target_start_date: string;
  status: string;
}

interface RecentHire {
  id: number;
  employee_number: string;
  name: string;
  cost_center_name: string;
  job_level: string;
  hire_date: string;
  base_salary: number;
  location: string;
  source: string;
}

interface HiringPlanResponse {
  open_positions: OpenPosition[];
  recent_hires: RecentHire[];
}

interface AssumptionItem {
  name: string;
  label: string;
  value: number | Record<string, number>;
  unit: string;
  display_value: string;
  description: string;
  used_in: string;
}

interface AssumptionCategory {
  name: string;
  category: string;
  items: AssumptionItem[];
}

interface SimulatorEvent {
  period: string;
  event_type: string;
  narrative: string;
  affected_area: string;
}

export default function DataAndAssumptions() {
  const [activeTab, setActiveTab] = useState<Tab>("Company");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("active");
  const [ccFilter, setCcFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("employee_number");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Data & Assumptions</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Inspect the data, hiring plan, and assumptions behind the forecast
        </p>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "Company" && (
        <CompanyTab
          search={search}
          setSearch={setSearch}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          ccFilter={ccFilter}
          setCcFilter={setCcFilter}
          page={page}
          setPage={setPage}
          sortBy={sortBy}
          setSortBy={setSortBy}
          sortDir={sortDir}
          setSortDir={setSortDir}
        />
      )}
      {activeTab === "Hiring Plan" && <HiringPlanTab />}
      {activeTab === "Forecast Assumptions" && <AssumptionsTab />}
      {activeTab === "Simulator Events" && <SimulatorEventsTab />}
    </div>
  );
}

// ---- Company Tab ----
function CompanyTab({
  search, setSearch, statusFilter, setStatusFilter,
  ccFilter, setCcFilter, page, setPage,
  sortBy, setSortBy, sortDir, setSortDir,
}: {
  search: string; setSearch: (v: string) => void;
  statusFilter: string; setStatusFilter: (v: string) => void;
  ccFilter: string; setCcFilter: (v: string) => void;
  page: number; setPage: (v: number) => void;
  sortBy: string; setSortBy: (v: string) => void;
  sortDir: "asc" | "desc"; setSortDir: (v: "asc" | "desc") => void;
}) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (statusFilter && statusFilter !== "all") params.set("status", statusFilter);
  if (ccFilter) params.set("cost_center_id", ccFilter);
  params.set("page", String(page));
  params.set("page_size", "50");
  params.set("sort_by", sortBy);
  params.set("sort_dir", sortDir);

  const { data, isLoading } = useQuery({
    queryKey: ["transparency-employees", search, statusFilter, ccFilter, page, sortBy, sortDir],
    queryFn: () => apiFetch<EmployeesResponse>(`/transparency/employees?${params.toString()}`),
  });

  const { data: costCenters } = useQuery({
    queryKey: ["cost-centers"],
    queryFn: () => apiFetch<CostCenter[]>("/cost-centers"),
  });

  const handleSort = (col: string) => {
    if (sortBy === col) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortBy(col);
      setSortDir("asc");
    }
  };

  const handleExport = () => {
    if (!data) return;
    const header = ["Employee ID", "Name", "Cost Center", "Level", "Location", "Hire Date", "Base Salary", "Status"];
    const rows = data.employees.map((e) => [
      e.employee_number, e.name, e.cost_center_name, e.job_level,
      e.location, e.hire_date, e.base_salary.toFixed(0), e.status,
    ]);
    const csv = [header, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "employees.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const totalPages = data ? Math.ceil(data.total / 50) : 0;

  const sortIndicator = (col: string) => {
    if (sortBy !== col) return "";
    return sortDir === "asc" ? " \u2191" : " \u2193";
  };

  const columns = [
    { key: "employee_number", label: "ID" },
    { key: "name", label: "Name" },
    { key: "cost_center_name", label: "Cost Center" },
    { key: "job_level", label: "Level" },
    { key: "location", label: "Location" },
    { key: "hire_date", label: "Hire Date" },
    { key: "base_salary", label: "Base Salary" },
    { key: "status", label: "Status" },
  ];

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 flex-wrap items-end">
        <div>
          <label className="text-xs text-muted-foreground block mb-1">Search</label>
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Name or ID..."
            className="px-3 py-1.5 text-sm border border-border rounded-md bg-card w-48"
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground block mb-1">Cost Center</label>
          <select
            value={ccFilter}
            onChange={(e) => { setCcFilter(e.target.value); setPage(1); }}
            className="px-3 py-1.5 text-sm rounded-md border border-border bg-card"
          >
            <option value="">All</option>
            {costCenters?.map((cc) => (
              <option key={cc.id} value={cc.id}>{cc.code} - {cc.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground block mb-1">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-3 py-1.5 text-sm rounded-md border border-border bg-card"
          >
            <option value="active">Active</option>
            <option value="terminated">Terminated</option>
            <option value="all">All</option>
          </select>
        </div>
        <button
          onClick={handleExport}
          className="px-3 py-1.5 text-sm font-medium rounded-md border border-border bg-card hover:bg-muted transition-colors"
        >
          Export CSV
        </button>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-muted-foreground text-center py-12">Loading employees...</div>
      ) : (
        <>
          <div className="text-xs text-muted-foreground">
            {data?.total} employees found
          </div>
          <div className="rounded-lg border border-border overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50">
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className="text-left px-4 py-3 font-medium text-muted-foreground cursor-pointer hover:text-foreground whitespace-nowrap"
                    >
                      {col.label}{sortIndicator(col.key)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data?.employees.map((emp, i) => (
                  <tr key={emp.id} className={i % 2 === 0 ? "bg-card" : "bg-muted/20"}>
                    <td className="px-4 py-2 font-mono text-xs">{emp.employee_number}</td>
                    <td className="px-4 py-2">{emp.name}</td>
                    <td className="px-4 py-2 text-sm">{emp.cost_center_name}</td>
                    <td className="px-4 py-2">{emp.job_level}</td>
                    <td className="px-4 py-2">{emp.location}</td>
                    <td className="px-4 py-2 whitespace-nowrap">{emp.hire_date}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{formatCurrency(emp.base_salary)}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        emp.status === "active" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
                      }`}>
                        {emp.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-sm rounded-md border border-border bg-card hover:bg-muted disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-3 py-1.5 text-sm rounded-md border border-border bg-card hover:bg-muted disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---- Hiring Plan Tab ----
function HiringPlanTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["transparency-hiring-plan"],
    queryFn: () => apiFetch<HiringPlanResponse>("/transparency/hiring-plan"),
  });

  if (isLoading) return <div className="text-muted-foreground text-center py-12">Loading hiring plan...</div>;

  return (
    <div className="space-y-8">
      {/* Open Positions */}
      <div>
        <h3 className="text-lg font-semibold mb-3">
          Open Positions ({data?.open_positions.length || 0})
        </h3>
        {data?.open_positions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No open positions.</p>
        ) : (
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Cost Center</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Level</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Target Start</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.open_positions.map((pos, i) => (
                  <tr key={pos.id} className={i % 2 === 0 ? "bg-card" : "bg-muted/20"}>
                    <td className="px-4 py-2">{pos.cost_center_name}</td>
                    <td className="px-4 py-2">{pos.job_level}</td>
                    <td className="px-4 py-2">{pos.target_start_date}</td>
                    <td className="px-4 py-2">
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        {pos.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Hires */}
      <div>
        <h3 className="text-lg font-semibold mb-3">
          Recent Hires — Last 6 Months ({data?.recent_hires.length || 0})
        </h3>
        {data?.recent_hires.length === 0 ? (
          <p className="text-sm text-muted-foreground">No recent hires.</p>
        ) : (
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Cost Center</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Level</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Hire Date</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Salary</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Source</th>
                </tr>
              </thead>
              <tbody>
                {data?.recent_hires.map((hire, i) => (
                  <tr key={hire.id} className={i % 2 === 0 ? "bg-card" : "bg-muted/20"}>
                    <td className="px-4 py-2">{hire.name}</td>
                    <td className="px-4 py-2">{hire.cost_center_name}</td>
                    <td className="px-4 py-2">{hire.job_level}</td>
                    <td className="px-4 py-2">{hire.hire_date}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{formatCurrency(hire.base_salary)}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        hire.source === "planned" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {hire.source}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Forecast Assumptions Tab ----
function AssumptionsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["transparency-assumptions"],
    queryFn: () => apiFetch<AssumptionCategory[]>("/transparency/assumptions"),
  });

  if (isLoading) return <div className="text-muted-foreground text-center py-12">Loading assumptions...</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {data?.map((category) => (
        <div key={category.category} className="rounded-lg border border-border bg-card p-5 space-y-4">
          <h3 className="font-semibold text-base">{category.name}</h3>
          {category.items.map((item) => (
            <div key={item.name} className="space-y-1">
              <div className="flex items-baseline justify-between">
                <p className="text-sm font-medium">{item.label}</p>
                <p className="text-lg font-semibold tabular-nums">{item.display_value}</p>
              </div>
              <p className="text-xs text-muted-foreground">{item.description}</p>
              <p className="text-xs text-muted-foreground/70 italic">Used in: {item.used_in}</p>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ---- Simulator Events Tab ----
function SimulatorEventsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["transparency-simulator-events"],
    queryFn: () => apiFetch<SimulatorEvent[]>("/transparency/simulator-events"),
  });

 

  // Group by period
  const grouped = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, SimulatorEvent[]>();
    for (const event of data) {
      const existing = map.get(event.period) || [];
      existing.push(event);
      map.set(event.period, existing);
    }
    return Array.from(map.entries());
  }, [data]);

 if (isLoading) return <div className="text-muted-foreground text-center py-12">Loading events...</div>;

  const eventTypeBadge: Record<string, string> = {
    unplanned_hire_cluster: "bg-blue-100 text-blue-800",
    premium_hire: "bg-purple-100 text-purple-800",
    unplanned_departures: "bg-red-100 text-red-800",
    cola_adjustment: "bg-green-100 text-green-800",
    retention_bonus_event: "bg-yellow-100 text-yellow-800",
    spot_bonus_event: "bg-orange-100 text-orange-800",
    overtime_event: "bg-pink-100 text-pink-800",
    reorganization: "bg-gray-100 text-gray-800",
  };

  return (
    <div className="space-y-4">
      {grouped.map(([period, events]) => (
        <div key={period} className="rounded-lg border border-border bg-card p-5">
          <h3 className="font-semibold text-sm text-muted-foreground mb-3">{period}</h3>
          {events.map((event, i) => (
            <div key={i} className="space-y-1">
              <div className="flex items-start gap-3">
                <span className={`px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${
                  eventTypeBadge[event.event_type] || "bg-gray-100 text-gray-800"
                }`}>
                  {event.event_type.replace(/_/g, " ")}
                </span>
                <p className="text-sm">{event.narrative}</p>
              </div>
              {event.affected_area && (
                <p className="text-xs text-muted-foreground ml-[calc(0.5rem+80px)]">
                  Affected area: {event.affected_area}
                </p>
              )}
            </div>
          ))}
        </div>
      ))}
      {grouped.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-8">No simulator events recorded.</p>
      )}
    </div>
  );
}
