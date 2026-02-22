"use client";

import { Badge } from "@/components/ui/badge";
import { getStateFromGSTIN } from "@/lib/format";

interface ClientHeaderProps {
  businessName: string;
  gstin: string | null;
  city: string | null;
  ingestEmail: string | null;
}

export function ClientHeader({ businessName, gstin, city, ingestEmail }: ClientHeaderProps) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">{businessName}</h1>
        {gstin && (
          <Badge variant="outline" className="font-mono text-xs">
            {gstin}
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        {gstin && <span>{getStateFromGSTIN(gstin)}</span>}
        {city && <span>{city}</span>}
        {ingestEmail && (
          <span>
            Ingest: <code className="bg-muted px-1 rounded text-xs">{ingestEmail}</code>
          </span>
        )}
      </div>
    </div>
  );
}
