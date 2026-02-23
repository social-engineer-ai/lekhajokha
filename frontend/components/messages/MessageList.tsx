"use client";

import { Message } from "@/lib/types/messaging";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: Message[];
  onRetry?: (id: string) => void;
}

function groupByDate(messages: Message[]): Map<string, Message[]> {
  const groups = new Map<string, Message[]>();
  for (const msg of messages) {
    const dateKey = new Date(msg.created_at).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
    if (!groups.has(dateKey)) {
      groups.set(dateKey, []);
    }
    groups.get(dateKey)!.push(msg);
  }
  return groups;
}

export function MessageList({ messages, onRetry }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p>No messages yet. Send your first message below.</p>
      </div>
    );
  }

  // Messages come newest-first from API, reverse for display (oldest first)
  const sorted = [...messages].reverse();
  const grouped = groupByDate(sorted);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3">
      {Array.from(grouped.entries()).map(([date, msgs]) => (
        <div key={date}>
          <div className="flex justify-center my-3">
            <span className="text-xs text-muted-foreground bg-muted px-3 py-1 rounded-full">
              {date}
            </span>
          </div>
          {msgs.map((msg) => (
            <MessageBubble key={msg.id} message={msg} onRetry={onRetry} />
          ))}
        </div>
      ))}
    </div>
  );
}
