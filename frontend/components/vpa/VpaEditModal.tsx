"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { VpaEntry } from "@/lib/types/vpa";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface VpaEditModalProps {
  entry: VpaEntry;
  clientId: string;
  onClose: () => void;
  onUpdated: () => void;
}

export function VpaEditModal({ entry, clientId, onClose, onUpdated }: VpaEditModalProps) {
  const [resolvedName, setResolvedName] = useState(entry.resolved_name || "");
  const [gstin, setGstin] = useState(entry.gstin || "");
  const [notes, setNotes] = useState(entry.notes || "");
  const [isVerified, setIsVerified] = useState(entry.is_verified);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await apiFetch(`/clients/${clientId}/vpa/${entry.id}`, {
        method: "PUT",
        body: JSON.stringify({
          resolved_name: resolvedName || null,
          gstin: gstin || null,
          notes: notes || null,
          is_verified: isVerified,
        }),
      });
      onUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update VPA");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-1">Edit VPA Entry</h3>
        <p className="text-sm text-muted-foreground mb-4 font-mono">{entry.vpa}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="edit-name">Name</Label>
            <Input
              id="edit-name"
              value={resolvedName}
              onChange={(e) => setResolvedName(e.target.value)}
              placeholder="Business name"
            />
          </div>
          <div>
            <Label htmlFor="edit-gstin">GSTIN</Label>
            <Input
              id="edit-gstin"
              value={gstin}
              onChange={(e) => setGstin(e.target.value)}
              placeholder="22AAAAA0000A1Z5"
              maxLength={15}
            />
          </div>
          <div>
            <Label htmlFor="edit-notes">Notes</Label>
            <Input
              id="edit-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any additional notes"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="edit-verified"
              checked={isVerified}
              onChange={(e) => setIsVerified(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="edit-verified">Mark as verified</Label>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
