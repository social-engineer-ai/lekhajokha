"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Job } from "@/lib/types/bank";
import { Badge } from "@/components/ui/badge";

interface ProcessingIndicatorProps {
  job: Job;
  onComplete: () => void;
}

export function ProcessingIndicator({ job: initialJob, onComplete }: ProcessingIndicatorProps) {
  const [job, setJob] = useState(initialJob);

  useEffect(() => {
    if (job.status === "completed" || job.status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const updated = await apiFetch<Job>(`/jobs/${job.id}`);
        setJob(updated);
        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(interval);
          onComplete();
        }
      } catch {
        // Ignore polling errors
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [job.id, job.status, onComplete]);

  return (
    <div className="flex items-center gap-3 rounded-lg border p-3 bg-muted/50">
      {(job.status === "pending" || job.status === "processing") && (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      )}

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Processing statement</span>
          <Badge
            variant={
              job.status === "completed"
                ? "default"
                : job.status === "failed"
                ? "destructive"
                : "secondary"
            }
          >
            {job.status}
          </Badge>
        </div>
        {job.result_summary && (
          <p className="text-xs text-muted-foreground mt-0.5">{job.result_summary}</p>
        )}
        {job.error_message && (
          <p className="text-xs text-destructive mt-0.5">{job.error_message}</p>
        )}
      </div>
    </div>
  );
}
