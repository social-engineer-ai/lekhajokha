"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface VpaAddModalProps {
  clientId: string;
  onClose: () => void;
  onCreated: () => void;
}

export function VpaAddModal({ clientId, onClose, onCreated }: VpaAddModalProps) {
  const [vpa, setVpa] = useState("");
  const [resolvedName, setResolvedName] = useState("");
  const [gstin, setGstin] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vpa || !vpa.includes("@")) {
      setError("VPA must contain @");
      return;
    }

    setSaving(true);
    setError("");
    try {
      await apiFetch(`/clients/${clientId}/vpa`, {
        method: "POST",
        body: JSON.stringify({
          vpa: vpa.trim().toLowerCase(),
          resolved_name: resolvedName || null,
          gstin: gstin || null,
          notes: notes || null,
        }),
      });
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add VPA");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Add VPA Entry</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="vpa">VPA / UPI ID *</Label>
            <Input
              id="vpa"
              value={vpa}
              onChange={(e) => setVpa(e.target.value)}
              placeholder="merchant@upi"
              required
            />
          </div>
          <div>
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={resolvedName}
              onChange={(e) => setResolvedName(e.target.value)}
              placeholder="Business name"
            />
          </div>
          <div>
            <Label htmlFor="gstin">GSTIN (optional)</Label>
            <Input
              id="gstin"
              value={gstin}
              onChange={(e) => setGstin(e.target.value)}
              placeholder="22AAAAA0000A1Z5"
              maxLength={15}
            />
          </div>
          <div>
            <Label htmlFor="notes">Notes</Label>
            <Input
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any additional notes"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Adding..." : "Add VPA"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
