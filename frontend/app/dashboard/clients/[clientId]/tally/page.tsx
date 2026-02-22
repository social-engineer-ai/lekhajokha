"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Job } from "@/lib/types/bank";
import { TallyConfig, TallySyncScope } from "@/lib/types/tally";
import { Separator } from "@/components/ui/separator";
import { ProcessingIndicator } from "@/components/bank/ProcessingIndicator";
import { TallySyncPanel } from "@/components/tally/TallySyncPanel";
import { SyncHistoryTable } from "@/components/tally/SyncHistoryTable";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function TallyPage() {
  const params = useParams();
  const clientId = params.clientId as string;

  const [tallyConfig, setTallyConfig] = useState<TallyConfig | null>(null);
  const [scope, setScope] = useState<TallySyncScope>("invoices_and_reconciled");
  const [syncJobs, setSyncJobs] = useState<Job[]>([]);
  const [runningJob, setRunningJob] = useState<Job | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [config, jobs] = await Promise.all([
        apiFetch<TallyConfig>("/tally/config"),
        apiFetch<Job[]>(`/jobs?client_id=${clientId}&job_type=tally_sync`).catch(() => [] as Job[]),
      ]);
      setTallyConfig(config);
      setSyncJobs(jobs);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleScopeChange = async (newScope: TallySyncScope) => {
    setScope(newScope);
    try {
      await apiFetch(`/clients/${clientId}`, {
        method: "PUT",
        body: JSON.stringify({ tally_sync_scope: newScope }),
      });
    } catch {
      // ignore
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const job = await apiFetch<Job>(`/tally/clients/${clientId}/sync`, {
        method: "POST",
        body: JSON.stringify({ scope }),
      });
      setRunningJob(job);
    } catch {
      // ignore
    } finally {
      setSyncing(false);
    }
  };

  const handleExport = async (month: number, year: number) => {
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_URL}/tally/clients/${clientId}/export`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ month, year, scope }),
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tally_export_${month}_${year}.xml`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  };

  const handleJobComplete = useCallback(() => {
    setRunningJob(null);
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-sm">Loading Tally integration...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Tally Integration</h2>
        <p className="text-sm text-muted-foreground">
          Sync invoices and transactions to Tally Prime, or export as XML
        </p>
      </div>

      {runningJob && (
        <ProcessingIndicator job={runningJob} onComplete={handleJobComplete} />
      )}

      <TallySyncPanel
        currentScope={scope}
        isConnected={tallyConfig?.is_connected ?? false}
        onScopeChange={handleScopeChange}
        onSync={handleSync}
        onExport={handleExport}
        syncing={syncing || !!runningJob}
      />

      <Separator />

      <div>
        <h3 className="text-sm font-medium mb-3">Sync History</h3>
        <SyncHistoryTable jobs={syncJobs} />
      </div>
    </div>
  );
}
