"use client";

import { Badge } from "@/components/ui/badge";
import type { Job } from "@/lib/types/bank";

interface SyncHistoryTableProps {
  jobs: Job[];
}

export function SyncHistoryTable({ jobs }: SyncHistoryTableProps) {
  if (jobs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-6">
        No sync history yet
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="pb-2 pr-4">Date</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2">Result</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-b last:border-0">
              <td className="py-2 pr-4">
                {new Date(job.created_at).toLocaleString("en-IN", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </td>
              <td className="py-2 pr-4">
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
              </td>
              <td className="py-2">
                {job.result_summary || job.error_message || "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
