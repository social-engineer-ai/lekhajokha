"use client";

import { ReconciliationMatch } from "@/lib/types/reconciliation";
import { MatchRow } from "./MatchRow";

interface MatchTableProps {
  matches: ReconciliationMatch[];
  clientId: string;
  onUpdate: () => void;
}

export function MatchTable({ matches, clientId, onUpdate }: MatchTableProps) {
  if (matches.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p className="text-sm">No matches found</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left px-3 py-2 font-medium">Invoice</th>
            <th className="text-left px-3 py-2 font-medium">Transaction</th>
            <th className="text-right px-3 py-2 font-medium">Amount</th>
            <th className="text-center px-3 py-2 font-medium">Confidence</th>
            <th className="text-center px-3 py-2 font-medium">Status</th>
            <th className="text-center px-3 py-2 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {matches.map((match) => (
            <MatchRow
              key={match.id}
              match={match}
              clientId={clientId}
              onUpdate={onUpdate}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
