import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import type { ForecastLine, ForecastVersionInfo, CostCenter } from "@/types/api";

const periodRanges = [
  { label: "Next 3 months", value: 3 },
  { label: "Next 6 months", value: 6 },
  { label: "Next 12 months", value: 12 },
  { label: "Full 18 months", value: 18 },
] as const;

export default function Forecast() {
  const [selectedCC, setSelectedCC] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedVersion, setSelectedVersion] = useState<string>("");
  const [periodRange, setPeriodRange] = useState<number>(18);

  const { data: costCenters } = useQuery({
    queryKey: ["cost-centers"],
    queryFn: () => apiFetch<CostCenter[]>("/cost-centers"),
  });

  const { data: versions } = useQuery({
    queryKey: ["forecast-versions"],
    queryFn: () => apiFetch<ForecastVersionInfo[]>("/forecast/versions"),
  });

  const { data: forecastData, isLoading } = useQuery({
    queryKey: ["forecast", selectedCC, selectedVersion],
    queryFn: () => {
      const params = new URLSearchParams();
      if (selectedCC) params.set("cost_center_id", selectedCC);
      if (selectedVersion) params.set("version_id", selectedVersion);
      const qs = params.toString();
      return apiFetch<ForecastLine[]>(`/forecast${qs ? `?${qs}` : ""}`);
    },
  });

  const allPeriods = useMemo(() => {
    if (!forecastData) return [];
    const set = new Set(forecastData.map((l) => l.period));
    return Array.from(set).sort();
  }, [forecastData]);

  // Apply period range filter
  const visiblePeriods = useMemo(() => {
    return allPeriods.slice(0, periodRange);
  }, [allPeriods, periodRange]);

  // Chart data: total comp expense by period
  const chartData = useMemo(() => {
    if (!forecastData) return [];
    const byPeriod = new Map<string, { salary: number; bonus: number; benefits: number; taxes: number }>();
    for (const line of forecastData) {
      if (!visiblePeriods.includes(line.period)) continue;
      const existing = byPeriod.get(line.period) || { salary: 0, bonus: 0, benefits: 0, taxes: 0 };
      if (line.category in existing) {
        existing[line.category as keyof typeof existing] += line.amount;
      }
      byPeriod.set(line.period, existing);
    }
    return visiblePeriods.map((period) => {
      const d = byPeriod.get(period) || { salary: 0, bonus: 0, benefits: 0, taxes: 0 };
      return {
        period,
        salary: Math.round(d.salary),
        bonus: Math.round(d.bonus),
        benefits: Math.round(d.benefits),
        taxes: Math.round(d.taxes),
        total: Math.round(d.salary + d.bonus + d.benefits + d.taxes),
      };
    });
  }, [forecastData, visiblePeriods]);

  // Group by period and category for table display
  const tableData = useMemo(() => {
    if (!forecastData) return [];

    const filtered = selectedCategory
      ? forecastData.filter((l) => l.category === selectedCategory)
      : forecastData;

    // Only include visible periods
    const periodFiltered = filtered.filter((l) => visiblePeriods.includes(l.period));

    // Group by cost_center_name + period
    const grouped = new Map<string, Map<string, { amount: number; headcount: number }>>();

    for (const line of periodFiltered) {
      const key = line.cost_center_name;
      if (!grouped.has(key)) grouped.set(key, new Map());
      const periods = grouped.get(key)!;

      const existing = periods.get(line.period) || { amount: 0, headcount: 0 };
      existing.amount += line.amount;
      existing.headcount = line.headcount_eop;
      periods.set(line.period, existing);
    }

    return Array.from(grouped.entries()).map(([ccName, periods]) => ({
      costCenter: ccName,
      periods: Object.fromEntries(periods),
    }));
  }, [forecastData, selectedCategory, visiblePeriods]);

  const categories = ["salary", "bonus", "benefits", "taxes"];

  const handleExport = () => {
    if (!forecastData) return;
    const header = ["Cost Center", "Period", "Category", "Amount", "Headcount"];
    const rows = forecastData.map((l) => [
      l.cost_center_name,
      l.period,
      l.category,
      l.amount.toFixed(2),
      l.headcount_eop.toString(),
    ]);
    const csv = [header, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "forecast.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Forecast</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {selectedVersion
              ? `Viewing version: ${versions?.find((v) => String(v.id) === selectedVersion)?.name || `v${selectedVersion}`}`
              : `Active forecast: ${versions?.find((v) => v.is_active)?.name || "Initial Plan FY26"}`}
          </p>
        </div>
        <button
          onClick={handleExport}
          className="px-4 py-2 text-sm font-medium rounded-md border border-border bg-card hover:bg-muted transition-colors"
        >
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <select
          value={selectedVersion}
          onChange={(e) => setSelectedVersion(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-card"
        >
          <option value="">Active Version</option>
          {versions?.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name} {v.is_active ? "(active)" : ""} — {v.source?.replace(/_/g, " ") || "initial plan"}
            </option>
          ))}
        </select>
        <select
          value={selectedCC}
          onChange={(e) => setSelectedCC(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-card"
        >
          <option value="">All Cost Centers</option>
          {costCenters?.map((cc) => (
            <option key={cc.id} value={cc.id}>
              {cc.code} - {cc.name}
            </option>
          ))}
        </select>
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-md border border-border bg-card"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Period range selector */}
      <div className="flex gap-2">
        {periodRanges.map((r) => (
          <button
            key={r.value}
            onClick={() => setPeriodRange(r.value)}
            className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
              periodRange === r.value
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border bg-card hover:bg-muted"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Forecast projection chart */}
      {chartData.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">
            Forward Forecast Projection — Total Comp Expense by Category
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="period" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" height={50} />
              <YAxis
                tickFormatter={(v: number) => `$${(v / 1_000_000).toFixed(1)}M`}
                tick={{ fontSize: 12 }}
              />
              <Tooltip
                formatter={(value: number, name: string) => [formatCurrency(value), name.charAt(0).toUpperCase() + name.slice(1)]}
                labelStyle={{ fontWeight: 600 }}
              />
              <Legend />
              <Line dataKey="salary" name="Salary" stroke="#3b82f6" strokeWidth={2} dot={false} />
              <Line dataKey="bonus" name="Bonus" stroke="#f59e0b" strokeWidth={2} dot={false} />
              <Line dataKey="benefits" name="Benefits" stroke="#10b981" strokeWidth={2} dot={false} />
              <Line dataKey="taxes" name="Taxes" stroke="#8b5cf6" strokeWidth={2} dot={false} />
              <Line dataKey="total" name="Total" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="text-muted-foreground text-center py-12">
          Loading forecast data...
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground sticky left-0 bg-muted/50 z-10 min-w-[180px]">
                  Cost Center
                </th>
                {visiblePeriods.map((p) => (
                  <th
                    key={p}
                    className="text-right px-4 py-3 font-medium text-muted-foreground whitespace-nowrap"
                  >
                    {p}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableData.map((row, i) => (
                <tr
                  key={row.costCenter}
                  className={i % 2 === 0 ? "bg-card" : "bg-muted/20"}
                >
                  <td className="px-4 py-2 font-medium sticky left-0 bg-inherit z-10">
                    {row.costCenter}
                  </td>
                  {visiblePeriods.map((p) => (
                    <td key={p} className="text-right px-4 py-2 tabular-nums whitespace-nowrap">
                      {row.periods[p]
                        ? formatCurrency(row.periods[p].amount)
                        : "-"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {tableData.length === 0 && (
            <p className="text-center text-muted-foreground py-8">
              No forecast data available.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
