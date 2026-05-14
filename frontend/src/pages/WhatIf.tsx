import { useState, useMemo, useEffect, useCallback } from "react";
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

interface ScenarioLine {
  period: string;
  category: string;
  amount: number;
}

interface DeltaSummary {
  total_18_month: number;
  fy_landing: number;
  by_category: Record<string, number>;
}

interface WhatIfResponse {
  scenario_lines: ScenarioLine[];
  baseline_lines: ScenarioLine[];
  delta: DeltaSummary;
}

interface DialConfig {
  key: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  defaultValue: number;
  displayMultiplier: number;
  displaySuffix: string;
}

const DIALS: DialConfig[] = [
  {
    key: "attrition_rate",
    label: "Annual Attrition Rate",
    unit: "%",
    min: 0.05,
    max: 0.25,
    step: 0.01,
    defaultValue: 0.12,
    displayMultiplier: 100,
    displaySuffix: "%",
  },
  {
    key: "merit_pct",
    label: "Merit Increase",
    unit: "%",
    min: 0.0,
    max: 0.10,
    step: 0.005,
    defaultValue: 0.04,
    displayMultiplier: 100,
    displaySuffix: "%",
  },
  {
    key: "benefits_load_pct",
    label: "Benefits Load",
    unit: "%",
    min: 0.10,
    max: 0.25,
    step: 0.01,
    defaultValue: 0.18,
    displayMultiplier: 100,
    displaySuffix: "%",
  },
  {
    key: "hire_pace_per_quarter",
    label: "Hire Pace / Quarter",
    unit: "%",
    min: 0.0,
    max: 0.05,
    step: 0.005,
    defaultValue: 0.02,
    displayMultiplier: 100,
    displaySuffix: "%",
  },
  {
    key: "headcount_acceleration_multiplier",
    label: "Headcount Acceleration",
    unit: "x",
    min: 0.5,
    max: 1.5,
    step: 0.1,
    defaultValue: 1.0,
    displayMultiplier: 1,
    displaySuffix: "x",
  },
];

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export default function WhatIf() {
  const defaultValues = Object.fromEntries(
    DIALS.map((d) => [d.key, d.defaultValue])
  );

  const [values, setValues] = useState<Record<string, number>>(defaultValues);
  const debouncedValues = useDebounce(values, 500);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["what-if", debouncedValues],
    queryFn: () =>
      apiFetch<WhatIfResponse>("/what-if/run", {
        method: "POST",
        body: JSON.stringify(debouncedValues),
      }),
  });

  const handleChange = useCallback((key: string, val: number) => {
    setValues((prev) => ({ ...prev, [key]: val }));
  }, []);

  const handleReset = useCallback((key: string) => {
    const dial = DIALS.find((d) => d.key === key);
    if (dial) handleChange(key, dial.defaultValue);
  }, [handleChange]);

  const handleResetAll = useCallback(() => {
    setValues(defaultValues);
  }, []);

  const isModified = useMemo(() => {
    return DIALS.some((d) => values[d.key] !== d.defaultValue);
  }, [values]);

  // Chart data: aggregate by period for scenario and baseline
  const chartData = useMemo(() => {
    if (!data) return [];

    const scenarioByPeriod = new Map<string, number>();
    for (const line of data.scenario_lines) {
      scenarioByPeriod.set(line.period, (scenarioByPeriod.get(line.period) || 0) + line.amount);
    }

    const baselineByPeriod = new Map<string, number>();
    for (const line of data.baseline_lines) {
      baselineByPeriod.set(line.period, (baselineByPeriod.get(line.period) || 0) + line.amount);
    }

    const allPeriods = Array.from(
      new Set([...scenarioByPeriod.keys(), ...baselineByPeriod.keys()])
    ).sort();

    return allPeriods.map((period) => ({
      period,
      baseline: Math.round(baselineByPeriod.get(period) || 0),
      scenario: Math.round(scenarioByPeriod.get(period) || 0),
    }));
  }, [data]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">What-If Scenario Simulator</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Adjust assumptions and see how the forecast changes
        </p>
      </div>

      {/* Disclaimer banner */}
      <div className="rounded-lg border border-blue-300 bg-blue-50 p-3">
        <p className="text-sm text-blue-800">
          This is a scenario. Changes are not saved and do not affect proposals or the active forecast.
        </p>
      </div>

      <div className="flex gap-6">
        {/* Left: Dials */}
        <div className="w-72 flex-shrink-0 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">Assumptions</h3>
            {isModified && (
              <button
                onClick={handleResetAll}
                className="text-xs text-primary hover:underline"
              >
                Reset All
              </button>
            )}
          </div>

          {DIALS.map((dial) => {
            const val = values[dial.key];
            const isChanged = val !== dial.defaultValue;
            return (
              <div key={dial.key} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">{dial.label}</label>
                  <span className={`text-sm font-semibold tabular-nums ${isChanged ? "text-primary" : ""}`}>
                    {(val * dial.displayMultiplier).toFixed(dial.step < 0.01 ? 2 : 1)}
                    {dial.displaySuffix}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={dial.min}
                    max={dial.max}
                    step={dial.step}
                    value={val}
                    onChange={(e) => handleChange(dial.key, parseFloat(e.target.value))}
                    className="flex-1 h-2 accent-primary"
                  />
                  {isChanged && (
                    <button
                      onClick={() => handleReset(dial.key)}
                      className="text-xs text-muted-foreground hover:text-foreground"
                      title="Reset to default"
                    >
                      reset
                    </button>
                  )}
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>
                    {(dial.min * dial.displayMultiplier).toFixed(dial.step < 0.01 ? 1 : 0)}
                    {dial.displaySuffix}
                  </span>
                  <span>
                    {(dial.max * dial.displayMultiplier).toFixed(dial.step < 0.01 ? 1 : 0)}
                    {dial.displaySuffix}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Chart and delta */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* Loading indicator */}
          {(isLoading || isFetching) && (
            <div className="text-sm text-muted-foreground">
              Recalculating scenario...
            </div>
          )}

          {/* Chart */}
          {chartData.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="text-sm font-medium text-muted-foreground mb-4">
                Active Forecast vs. Scenario — Total Monthly Comp
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
                    formatter={(value: number, name: string) => [
                      formatCurrency(value),
                      name === "baseline" ? "Active Forecast" : "Scenario",
                    ]}
                    labelStyle={{ fontWeight: 600 }}
                  />
                  <Legend
                    formatter={(value: string) =>
                      value === "baseline" ? "Active Forecast" : "Scenario"
                    }
                  />
                  <Line
                    dataKey="baseline"
                    name="baseline"
                    stroke="#94a3b8"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                  <Line
                    dataKey="scenario"
                    name="scenario"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Delta summary */}
          {data?.delta && (
            <div className="rounded-lg border border-border bg-card p-5 space-y-4">
              <h3 className="text-sm font-medium text-muted-foreground">
                Delta vs. Active Forecast
              </h3>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">
                    Total 18-Month Impact
                  </p>
                  <p className={`text-xl font-semibold tabular-nums ${
                    data.delta.total_18_month > 0 ? "text-red-600" : data.delta.total_18_month < 0 ? "text-green-600" : ""
                  }`}>
                    {data.delta.total_18_month > 0 ? "+" : ""}
                    {formatCurrency(data.delta.total_18_month)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">
                    FY Landing Impact
                  </p>
                  <p className={`text-xl font-semibold tabular-nums ${
                    data.delta.fy_landing > 0 ? "text-red-600" : data.delta.fy_landing < 0 ? "text-green-600" : ""
                  }`}>
                    {data.delta.fy_landing > 0 ? "+" : ""}
                    {formatCurrency(data.delta.fy_landing)}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
                  Breakdown by Category
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {Object.entries(data.delta.by_category).map(([cat, val]) => (
                    <div key={cat} className="rounded-md bg-muted/30 p-3">
                      <p className="text-xs text-muted-foreground capitalize">{cat}</p>
                      <p className={`text-sm font-semibold tabular-nums ${
                        val > 0 ? "text-red-600" : val < 0 ? "text-green-600" : ""
                      }`}>
                        {val > 0 ? "+" : ""}
                        {formatCurrency(val)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
