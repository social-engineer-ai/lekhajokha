"use client";

import { Message } from "@/lib/types/messaging";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface MessageBubbleProps {
  message: Message;
  onRetry?: (id: string) => void;
}

export function MessageBubble({ message, onRetry }: MessageBubbleProps) {
  const isOutbound = message.direction === "outbound";

  const statusColor =
    message.status === "sent" || message.status === "delivered" || message.status === "read"
      ? "default"
      : message.status === "failed"
      ? "destructive"
      : "secondary";

  const channelIcon = message.channel === "whatsapp" ? "WA" : "EM";

  return (
    <div className={`flex ${isOutbound ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[70%] rounded-lg p-3 ${
          isOutbound
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        }`}
      >
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-mono opacity-70">{channelIcon}</span>
          {message.subject && (
            <span className="text-xs font-medium">{message.subject}</span>
          )}
          {message.message_type === "notification" && (
            <Badge variant="outline" className="text-[10px] px-1 py-0">auto</Badge>
          )}
        </div>

        <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>

        {message.attachment_name && (
          <div className="mt-1 text-xs opacity-80">
            📎 {message.attachment_name}
          </div>
        )}

        <div className="flex items-center gap-2 mt-2">
          <span className="text-[10px] opacity-60">
            {new Date(message.created_at).toLocaleString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
              day: "numeric",
              month: "short",
            })}
          </span>
          {isOutbound && (
            <Badge variant={statusColor} className="text-[10px] px-1 py-0">
              {message.status}
            </Badge>
          )}
          {message.status === "failed" && onRetry && (
            <Button
              size="sm"
              variant="ghost"
              className="h-5 px-1 text-[10px]"
              onClick={() => onRetry(message.id)}
            >
              Retry
            </Button>
          )}
        </div>

        {message.error_message && (
          <p className="text-[10px] text-destructive mt-1">{message.error_message}</p>
        )}
      </div>
    </div>
  );
}
