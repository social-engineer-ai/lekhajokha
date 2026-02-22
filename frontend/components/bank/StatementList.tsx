"use client";

import { BankStatement } from "@/lib/types/bank";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/format";

interface StatementListProps {
  statements: BankStatement[];
}

export function StatementList({ statements }: StatementListProps) {
  if (statements.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No statements uploaded yet.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Uploaded Statements</h3>
      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="text-left p-2 font-medium">File</th>
              <th className="text-left p-2 font-medium">Period</th>
              <th className="text-right p-2 font-medium">Txns</th>
              <th className="text-left p-2 font-medium">Status</th>
              <th className="text-left p-2 font-medium">Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {statements.map((stmt) => (
              <tr key={stmt.id} className="border-b last:border-0">
                <td className="p-2">
                  <span className="truncate block max-w-[200px]">{stmt.file_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {(stmt.file_size_bytes / 1024).toFixed(0)} KB
                    {stmt.is_password_protected && " (encrypted)"}
                  </span>
                </td>
                <td className="p-2 text-xs">
                  {stmt.period_from && stmt.period_to
                    ? `${formatDate(stmt.period_from)} - ${formatDate(stmt.period_to)}`
                    : "-"}
                </td>
                <td className="p-2 text-right tabular-nums">{stmt.transactions_count}</td>
                <td className="p-2">
                  <Badge
                    variant={
                      stmt.processing_status === "completed"
                        ? "default"
                        : stmt.processing_status === "failed"
                        ? "destructive"
                        : "secondary"
                    }
                  >
                    {stmt.processing_status}
                  </Badge>
                </td>
                <td className="p-2 text-xs text-muted-foreground">
                  {formatDate(stmt.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
