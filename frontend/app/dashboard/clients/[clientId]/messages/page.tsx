"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Message } from "@/lib/types/messaging";
import { ChannelFilter } from "@/components/messages/ChannelFilter";
import { MessageList } from "@/components/messages/MessageList";
import { ComposeBar } from "@/components/messages/ComposeBar";

export default function MessagesPage() {
  const params = useParams();
  const clientId = params.clientId as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [channel, setChannel] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const fetchMessages = useCallback(async () => {
    try {
      const query = channel ? `?channel=${channel}&limit=100` : "?limit=100";
      const data = await apiFetch<Message[]>(
        `/clients/${clientId}/messages${query}`
      );
      setMessages(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [clientId, channel]);

  useEffect(() => {
    fetchMessages();
    // Poll every 10 seconds for new messages
    const interval = setInterval(fetchMessages, 10000);
    return () => clearInterval(interval);
  }, [fetchMessages]);

  const handleSend = async (data: {
    channel: string;
    content: string;
    subject?: string;
  }) => {
    setSending(true);
    try {
      await apiFetch(`/clients/${clientId}/messages`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      await fetchMessages();
    } catch {
      // ignore
    } finally {
      setSending(false);
    }
  };

  const handleRetry = async (messageId: string) => {
    try {
      await apiFetch(`/clients/${clientId}/messages/${messageId}/resend`, {
        method: "POST",
      });
      await fetchMessages();
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      <div className="flex items-center justify-between pb-3 border-b">
        <h2 className="text-lg font-medium">Messages</h2>
        <ChannelFilter selected={channel} onChange={setChannel} />
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <MessageList messages={messages} onRetry={handleRetry} />
      )}

      <ComposeBar onSend={handleSend} sending={sending} />
    </div>
  );
}
