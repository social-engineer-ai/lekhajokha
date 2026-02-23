"use client";

import { useState } from "react";
import { MessageTemplate } from "@/lib/types/messaging";
import { apiFetch } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface NotificationTemplateListProps {
  templates: MessageTemplate[];
  onUpdate: () => void;
}

const TRIGGER_LABELS: Record<string, string> = {
  statement_processed: "Bank Statement Processed",
  invoice_ocr_done: "Invoice OCR Done",
  reconciliation_complete: "Reconciliation Complete",
  gst_return_ready: "GST Return Ready",
  tally_sync_done: "Tally Sync Done",
  payment_reminder: "Payment Reminder",
};

export function NotificationTemplateList({
  templates,
  onUpdate,
}: NotificationTemplateListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [editSubject, setEditSubject] = useState("");
  const [saving, setSaving] = useState(false);

  const grouped = templates.reduce<Record<string, MessageTemplate[]>>((acc, t) => {
    if (!acc[t.trigger_event]) acc[t.trigger_event] = [];
    acc[t.trigger_event].push(t);
    return acc;
  }, {});

  const handleExpand = (t: MessageTemplate) => {
    if (expandedId === t.id) {
      setExpandedId(null);
    } else {
      setExpandedId(t.id);
      setEditBody(t.body_template);
      setEditSubject(t.subject_template || "");
    }
  };

  const handleSave = async (templateId: string) => {
    setSaving(true);
    try {
      const body: Record<string, string> = { body_template: editBody };
      if (editSubject) body.subject_template = editSubject;
      await apiFetch(`/messaging/templates/${templateId}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
      onUpdate();
      setExpandedId(null);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (templateId: string) => {
    try {
      await apiFetch(`/messaging/templates/${templateId}/toggle`, {
        method: "POST",
      });
      onUpdate();
    } catch {
      // ignore
    }
  };

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([trigger, tmpls]) => (
        <div key={trigger} className="border rounded-lg p-3">
          <h4 className="text-sm font-medium mb-2">
            {TRIGGER_LABELS[trigger] || trigger}
          </h4>
          <div className="space-y-2">
            {tmpls.map((t) => (
              <div key={t.id} className="border rounded p-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={t.channel === "whatsapp" ? "default" : "secondary"}
                    >
                      {t.channel}
                    </Badge>
                    {!t.accountant_id && (
                      <span className="text-[10px] text-muted-foreground">
                        (system default)
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 text-xs"
                      onClick={() => handleToggle(t.id)}
                    >
                      {t.is_active ? "Disable" : "Enable"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 text-xs"
                      onClick={() => handleExpand(t)}
                    >
                      {expandedId === t.id ? "Close" : "Edit"}
                    </Button>
                    <Badge variant={t.is_active ? "default" : "secondary"}>
                      {t.is_active ? "On" : "Off"}
                    </Badge>
                  </div>
                </div>

                {expandedId !== t.id && (
                  <p className="text-xs text-muted-foreground mt-1 truncate">
                    {t.body_template}
                  </p>
                )}

                {expandedId === t.id && (
                  <div className="mt-2 space-y-2">
                    {t.channel === "email" && (
                      <div>
                        <Label className="text-xs">Subject</Label>
                        <Input
                          value={editSubject}
                          onChange={(e) => setEditSubject(e.target.value)}
                          className="h-8 text-xs"
                        />
                      </div>
                    )}
                    <div>
                      <Label className="text-xs">Body</Label>
                      <textarea
                        value={editBody}
                        onChange={(e) => setEditBody(e.target.value)}
                        className="w-full border rounded p-2 text-xs min-h-[80px] resize-y"
                      />
                    </div>
                    <p className="text-[10px] text-muted-foreground">
                      Variables: {"{{client_name}}"}, {"{{firm_name}}"}, and
                      trigger-specific like {"{{bank_name}}"}, {"{{txn_count}}"}, etc.
                    </p>
                    <Button
                      size="sm"
                      onClick={() => handleSave(t.id)}
                      disabled={saving}
                    >
                      {saving ? "Saving..." : "Save"}
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
