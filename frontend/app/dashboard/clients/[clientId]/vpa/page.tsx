"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Job } from "@/lib/types/bank";
import { VpaEntry, VpaResolutionSummary } from "@/lib/types/vpa";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ProcessingIndicator } from "@/components/bank/ProcessingIndicator";
import { VpaSummaryCards } from "@/components/vpa/VpaSummaryCards";
import { VpaDirectory } from "@/components/vpa/VpaDirectory";
import { VpaAddModal } from "@/components/vpa/VpaAddModal";
import { VpaEditModal } from "@/components/vpa/VpaEditModal";

export default function VpaPage() {
  const params = useParams();
  const clientId = params.clientId as string;

  const [summary, setSummary] = useState<VpaResolutionSummary | null>(null);
  const [entries, setEntries] = useState<VpaEntry[]>([]);
  const [runningJob, setRunningJob] = useState<Job | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [editEntry, setEditEntry] = useState<VpaEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [collectMsg, setCollectMsg] = useState<{ text: string; isError: boolean } | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [summaryData, entriesData] = await Promise.all([
        apiFetch<VpaResolutionSummary>(`/clients/${clientId}/vpa/summary`),
        apiFetch<VpaEntry[]>(`/clients/${clientId}/vpa`),
      ]);
      setSummary(summaryData);
      setEntries(entriesData);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleResolve = async () => {
    setResolving(true);
    try {
      const job = await apiFetch<Job>(`/clients/${clientId}/vpa/resolve`, {
        method: "POST",
      });
      setRunningJob(job);
    } catch {
      // ignore
    } finally {
      setResolving(false);
    }
  };

  const handleCollect = async () => {
    setCollecting(true);
    setCollectMsg(null);
    try {
      const result = await apiFetch<{ message?: string }>(`/clients/${clientId}/vpa/collect`, { method: "POST" });
      setCollectMsg({ text: result.message || "Collection request sent", isError: false });
    } catch (err: unknown) {
      setCollectMsg({ text: err instanceof Error ? err.message : "Failed to send collection request", isError: true });
    } finally {
      setCollecting(false);
      setTimeout(() => setCollectMsg(null), 5000);
    }
  };

  const handleJobComplete = useCallback(() => {
    setRunningJob(null);
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-sm">Loading VPA data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">UPI VPA Directory</h2>
          <p className="text-sm text-muted-foreground">
            Identify and verify UPI VPA owners for payment verification
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCollect} disabled={collecting}>
            {collecting ? "Sending..." : "Request from Client"}
          </Button>
          <Button variant="outline" onClick={() => setShowAdd(true)}>
            Add VPA
          </Button>
          <Button onClick={handleResolve} disabled={resolving || !!runningJob}>
            {resolving ? "Starting..." : "Resolve VPAs"}
          </Button>
        </div>
      </div>

      {/* Collect feedback message */}
      {collectMsg && (
        <p className={`text-sm ${collectMsg.isError ? "text-destructive" : "text-green-600"}`}>
          {collectMsg.text}
        </p>
      )}

      {/* Processing indicator */}
      {runningJob && (
        <ProcessingIndicator job={runningJob} onComplete={handleJobComplete} />
      )}

      {/* Summary cards */}
      {summary && <VpaSummaryCards summary={summary} />}

      <Separator />

      {/* VPA directory table */}
      <VpaDirectory
        entries={entries}
        clientId={clientId}
        onUpdate={fetchData}
        onEdit={setEditEntry}
      />

      {/* Add modal */}
      {showAdd && (
        <VpaAddModal
          clientId={clientId}
          onClose={() => setShowAdd(false)}
          onCreated={() => {
            setShowAdd(false);
            fetchData();
          }}
        />
      )}

      {/* Edit modal */}
      {editEntry && (
        <VpaEditModal
          entry={editEntry}
          clientId={clientId}
          onClose={() => setEditEntry(null)}
          onUpdated={() => {
            setEditEntry(null);
            fetchData();
          }}
        />
      )}
    </div>
  );
}
