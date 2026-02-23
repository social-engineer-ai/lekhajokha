"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface ComposeBarProps {
  onSend: (data: {
    channel: string;
    content: string;
    subject?: string;
  }) => void;
  sending?: boolean;
}

export function ComposeBar({ onSend, sending }: ComposeBarProps) {
  const [channel, setChannel] = useState<"whatsapp" | "email">("whatsapp");
  const [content, setContent] = useState("");
  const [subject, setSubject] = useState("");

  const handleSend = () => {
    if (!content.trim()) return;
    onSend({
      channel,
      content: content.trim(),
      subject: channel === "email" ? subject.trim() || undefined : undefined,
    });
    setContent("");
    setSubject("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t p-3 space-y-2">
      <div className="flex gap-1">
        <Button
          size="sm"
          variant={channel === "whatsapp" ? "default" : "outline"}
          onClick={() => setChannel("whatsapp")}
        >
          WhatsApp
        </Button>
        <Button
          size="sm"
          variant={channel === "email" ? "default" : "outline"}
          onClick={() => setChannel("email")}
        >
          Email
        </Button>
      </div>

      {channel === "email" && (
        <Input
          placeholder="Subject (optional)"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
        />
      )}

      <div className="flex gap-2">
        <Input
          placeholder={`Type a ${channel === "whatsapp" ? "WhatsApp" : "email"} message...`}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1"
        />
        <Button onClick={handleSend} disabled={sending || !content.trim()}>
          {sending ? "Sending..." : "Send"}
        </Button>
      </div>
    </div>
  );
}
