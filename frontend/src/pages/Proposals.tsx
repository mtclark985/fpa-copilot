import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { Proposal } from "@/types/api";

const statusFilters = ["pending", "accepted", "rejected", "all"] as const;
type StatusFilter = (typeof statusFilters)[number];

const confidenceBadge: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-red-100 text-red-800",
};

const statusBadge: Record<string, string> = {
  pending: "bg-blue-100 text-blue-800",
  accepted: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  modified_and_accepted: "bg-green-100 text-green-800",
  superseded: "bg-gray-100 text-gray-800",
};

export default function Proposals() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [modifyingId, setModifyingId] = useState<number | null>(null);
  const [modifyDelta, setModifyDelta] = useState("");
  const [noteText, setNoteText] = useState("");
  const [actionId, setActionId] = useState<number | null>(null);
  const [actionType, setActionType] = useState<string | null>(null);

  const queryParams =
    statusFilter === "all" ? "" : `?status=${statusFilter}`;

  const { data: proposals, isLoading } = useQuery({
    queryKey: ["proposals", statusFilter],
    queryFn: () =>
      apiFetch<Proposal[]>(`/proposals${queryParams}`),
  });

  const acceptMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      apiFetch(`/proposals/${id}/accept`, {
        method: "POST",
        body: JSON.stringify({ note: note || null }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries();
      resetAction();
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      apiFetch(`/proposals/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ note: note || null }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries();
      resetAction();
    },
  });

  const modifyMutation = useMutation({
    mutationFn: ({
      id,
      modified_delta_per_period,
      note,
    }: {
      id: number;
      modified_delta_per_period: number;
      note?: string;
    }) =>
      apiFetch(`/proposals/${id}/modify-and-accept`, {
        method: "POST",
        body: JSON.stringify({ modified_delta_per_period, note: note || null }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries();
      resetAction();
      setModifyingId(null);
    },
  });

  function resetAction() {
    setActionId(null);
    setActionType(null);
    setNoteText("");
  }

  function startAction(id: number, type: string) {
    setActionId(id);
    setActionType(type);
    setNoteText("");
  }

  const isPending =
    acceptMutation.isPending ||
    rejectMutation.isPending ||
    modifyMutation.isPending;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Proposals</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Review and act on forecast update proposals from the AI agent
        </p>
      </div>

      {/* Status filter chips */}
      <div className="flex gap-2">
        {statusFilters.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 text-sm rounded-md border transition-colors capitalize ${
              statusFilter === s
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border bg-card hover:bg-muted"
            }`}
          >
            {s === "all" ? "All" : s}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-muted-foreground text-center py-12">
          Loading proposals...
        </div>
      ) : proposals?.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">
            No {statusFilter !== "all" ? statusFilter : ""} proposals found.
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            Advance a month on the Close page to generate new proposals.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {proposals?.map((p) => (
            <div
              key={p.id}
              className="rounded-lg border border-border bg-card overflow-hidden"
            >
              {/* Card header */}
              <div className="p-5 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-semibold text-base">
                      {p.cost_center_name}{" "}
                      <span className="text-muted-foreground font-normal">
                        / {p.category}
                      </span>
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Period: {p.created_for_period} | Affects:{" "}
                      {p.affected_periods[0]} – {p.affected_periods[p.affected_periods.length - 1]}{" "}
                      ({p.affected_periods.length} months)
                    </p>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${confidenceBadge[p.confidence] || "bg-gray-100 text-gray-800"}`}
                    >
                      {p.confidence}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${statusBadge[p.status] || "bg-gray-100 text-gray-800"}`}
                    >
                      {p.status.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>

                {/* Dollar impact */}
                <div className="flex gap-6">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">
                      Per Month
                    </p>
                    <p
                      className={`text-lg font-semibold tabular-nums ${
                        p.delta_per_period > 0
                          ? "text-red-600"
                          : "text-green-600"
                      }`}
                    >
                      {p.delta_per_period > 0 ? "+" : ""}
                      {formatCurrency(p.delta_per_period)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">
                      Total Impact
                    </p>
                    <p
                      className={`text-lg font-semibold tabular-nums ${
                        p.delta_per_period * p.affected_periods.length > 0
                          ? "text-red-600"
                          : "text-green-600"
                      }`}
                    >
                      {p.delta_per_period > 0 ? "+" : ""}
                      {formatCurrency(
                        p.delta_per_period * p.affected_periods.length
                      )}
                    </p>
                  </div>
                  {p.modified_delta_per_period !== null && (
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">
                        Modified Delta
                      </p>
                      <p className="text-lg font-semibold tabular-nums text-blue-600">
                        {p.modified_delta_per_period > 0 ? "+" : ""}
                        {formatCurrency(p.modified_delta_per_period)}
                      </p>
                    </div>
                  )}
                </div>

                {/* Rationale */}
                <div className="text-sm text-foreground/80">
                  {p.agent_rationale}
                </div>

                {/* Decision note */}
                {p.decision_note && (
                  <div className="text-sm text-muted-foreground italic border-l-2 border-border pl-3">
                    Note: {p.decision_note}
                  </div>
                )}

                {/* Expandable sections */}
                <button
                  onClick={() =>
                    setExpandedId(expandedId === p.id ? null : p.id)
                  }
                  className="text-xs text-primary hover:underline"
                >
                  {expandedId === p.id ? "Hide details" : "Show details"}
                </button>

                {expandedId === p.id && (
                  <div className="space-y-3 pt-2 border-t border-border">
                    {p.attributed_events.length > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
                          Attribution Detail
                        </p>
                        {p.attributed_events.map((evt, i) => (
                          <div
                            key={i}
                            className="text-sm bg-muted/30 rounded p-3 mb-2"
                          >
                            <span className="font-medium capitalize">
                              {evt.attribution_type?.replace(/_/g, " ")}
                            </span>
                            {evt.narrative && (
                              <p className="mt-1 text-muted-foreground">
                                {evt.narrative}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
                        Affected Periods
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {p.affected_periods.map((period) => (
                          <span
                            key={period}
                            className="px-2 py-0.5 bg-muted rounded text-xs"
                          >
                            {period}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Modify inline */}
                {modifyingId === p.id && p.status === "pending" && (
                  <div className="border-t border-border pt-3 space-y-2">
                    <label className="text-sm font-medium">
                      Modified delta per period ($)
                    </label>
                    <input
                      type="number"
                      value={modifyDelta}
                      onChange={(e) => setModifyDelta(e.target.value)}
                      className="w-48 px-3 py-1.5 text-sm border border-border rounded-md bg-background"
                      step="100"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          startAction(p.id, "modify")
                        }
                        disabled={!modifyDelta || isPending}
                        className="px-3 py-1.5 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        Accept Modified
                      </button>
                      <button
                        onClick={() => {
                          setModifyingId(null);
                          setModifyDelta("");
                        }}
                        className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-muted"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Note input for actions */}
                {actionId === p.id && (
                  <div className="border-t border-border pt-3 space-y-2">
                    <label className="text-sm font-medium">
                      Note (optional)
                    </label>
                    <input
                      type="text"
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      placeholder="Add a note..."
                      className="w-full px-3 py-1.5 text-sm border border-border rounded-md bg-background"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          if (actionType === "accept") {
                            acceptMutation.mutate({
                              id: p.id,
                              note: noteText,
                            });
                          } else if (actionType === "reject") {
                            rejectMutation.mutate({
                              id: p.id,
                              note: noteText,
                            });
                          } else if (actionType === "modify") {
                            modifyMutation.mutate({
                              id: p.id,
                              modified_delta_per_period: parseFloat(modifyDelta),
                              note: noteText,
                            });
                          }
                        }}
                        disabled={isPending}
                        className={`px-3 py-1.5 text-sm rounded-md text-white disabled:opacity-50 ${
                          actionType === "reject"
                            ? "bg-red-600 hover:bg-red-700"
                            : "bg-green-600 hover:bg-green-700"
                        }`}
                      >
                        {isPending
                          ? "Processing..."
                          : actionType === "reject"
                            ? "Confirm Reject"
                            : actionType === "modify"
                              ? "Confirm Modified Accept"
                              : "Confirm Accept"}
                      </button>
                      <button
                        onClick={resetAction}
                        className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-muted"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Action buttons (only for pending proposals, when no action in progress) */}
                {p.status === "pending" &&
                  actionId !== p.id &&
                  modifyingId !== p.id && (
                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={() => startAction(p.id, "accept")}
                        disabled={isPending}
                        className="px-4 py-1.5 text-sm rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => startAction(p.id, "reject")}
                        disabled={isPending}
                        className="px-4 py-1.5 text-sm rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => {
                          setModifyingId(p.id);
                          setModifyDelta(String(p.delta_per_period));
                        }}
                        disabled={isPending}
                        className="px-4 py-1.5 text-sm rounded-md border border-border hover:bg-muted disabled:opacity-50"
                      >
                        Modify
                      </button>
                    </div>
                  )}

                {/* Error display */}
                {(acceptMutation.isError ||
                  rejectMutation.isError ||
                  modifyMutation.isError) &&
                  actionId === p.id && (
                    <p className="text-sm text-destructive">
                      Error:{" "}
                      {(
                        (acceptMutation.error ||
                          rejectMutation.error ||
                          modifyMutation.error) as Error
                      )?.message}
                    </p>
                  )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
