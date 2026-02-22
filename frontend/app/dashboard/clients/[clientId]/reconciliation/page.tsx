"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Job } from "@/lib/types/bank";
import { ReconciliationMatch, ReconciliationSummary } from "@/lib/types/reconciliation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ProcessingIndicator } from "@/components/bank/ProcessingIndicator";
import { ReconSummaryCards } from "@/components/reconciliation/ReconSummaryCards";
import { MatchTable } from "@/components/reconciliation/MatchTable";
import { ManualMatchModal } from "@/components/reconciliation/ManualMatchModal";

type TabFilter = "all" | "confirmed" | "pending";

export default function ReconciliationPage() {
  const params = useParams();
  const clientId = params.clientId as string;

  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);
  const [matches, setMatches] = useState<ReconciliationMatch[]>([]);
  const [activeTab, setActiveTab] = useState<TabFilter>("all");
  const [runningJob, setRunningJob] = useState<Job | null>(null);
  const [showManualMatch, setShowManualMatch] = useState(false);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [summaryData, matchesData] = await Promise.all([
        apiFetch<ReconciliationSummary>(`/clients/${clientId}/reconciliation/summary`),
        apiFetch<ReconciliationMatch[]>(
          `/clients/${clientId}/reconciliation/matches${
            activeTab === "confirmed"
              ? "?is_confirmed=true"
              : activeTab === "pending"
              ? "?is_confirmed=false"
              : ""
          }`
        ),
      ]);
      setSummary(summaryData);
      setMatches(matchesData);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [clientId, activeTab]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRunAutoMatch = async () => {
    setRunning(true);
    try {
      const job = await apiFetch<Job>(`/clients/${clientId}/reconciliation/run`, {
        method: "POST",
      });
      setRunningJob(job);
    } catch {
      // ignore
    } finally {
      setRunning(false);
    }
  };

  const handleJobComplete = useCallback(() => {
    setRunningJob(null);
    fetchData();
  }, [fetchData]);

  const tabs: { key: TabFilter; label: string }[] = [
    { key: "all", label: "All Matches" },
    { key: "confirmed", label: "Confirmed" },
    { key: "pending", label: "Pending" },
  ];

  if (loading) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-sm">Loading reconciliation data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Reconciliation</h2>
          <p className="text-sm text-muted-foreground">
            Match invoices to bank transactions
          </p>
        </div>
        <Button onClick={handleRunAutoMatch} disabled={running || !!runningJob}>
          {running ? "Starting..." : "Run Auto-Match"}
        </Button>
      </div>

      {/* Processing indicator */}
      {runningJob && (
        <ProcessingIndicator job={runningJob} onComplete={handleJobComplete} />
      )}

      {/* Summary cards */}
      {summary && <ReconSummaryCards summary={summary} />}

      <Separator />

      {/* Tabs + Manual Match button */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                activeTab === tab.key
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowManualMatch(true)}>
          Manual Match
        </Button>
      </div>

      {/* Match table */}
      <MatchTable matches={matches} clientId={clientId} onUpdate={fetchData} />

      {/* Manual match modal */}
      {showManualMatch && (
        <ManualMatchModal
          clientId={clientId}
          onClose={() => setShowManualMatch(false)}
          onCreated={() => {
            setShowManualMatch(false);
            fetchData();
          }}
        />
      )}
    </div>
  );
}
