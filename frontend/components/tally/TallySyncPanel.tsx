"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PeriodPicker } from "@/components/gst/PeriodPicker";
import type { TallySyncScope } from "@/lib/types/tally";

interface TallySyncPanelProps {
  currentScope: TallySyncScope;
  isConnected: boolean;
  onScopeChange: (scope: TallySyncScope) => void;
  onSync: () => void;
  onExport: (month: number, year: number) => void;
  syncing: boolean;
}

const SCOPE_LABELS: Record<TallySyncScope, string> = {
  invoices_only: "Invoices Only",
  invoices_and_reconciled: "Invoices + Reconciled Pairs",
  all: "All (Invoices + Reconciled + Transactions)",
};

export function TallySyncPanel({
  currentScope,
  isConnected,
  onScopeChange,
  onSync,
  onExport,
  syncing,
}: TallySyncPanelProps) {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Tally Sync & Export</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scope selector */}
        <div>
          <label className="text-sm font-medium mb-1 block">Sync Scope</label>
          <select
            value={currentScope}
            onChange={(e) => onScopeChange(e.target.value as TallySyncScope)}
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
          >
            {(Object.keys(SCOPE_LABELS) as TallySyncScope[]).map((scope) => (
              <option key={scope} value={scope}>
                {SCOPE_LABELS[scope]}
              </option>
            ))}
          </select>
        </div>

        {/* Period picker for export */}
        <div>
          <label className="text-sm font-medium mb-1 block">Export Period</label>
          <PeriodPicker month={month} year={year} onMonthChange={setMonth} onYearChange={setYear} />
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {isConnected && (
            <Button onClick={onSync} disabled={syncing}>
              {syncing ? "Syncing..." : "Sync to Tally"}
            </Button>
          )}
          <Button variant="outline" onClick={() => onExport(month, year)}>
            Export XML
          </Button>
        </div>

        {!isConnected && (
          <p className="text-xs text-muted-foreground">
            Tally is not connected. Use Export XML to download, or configure Tally in Settings.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
