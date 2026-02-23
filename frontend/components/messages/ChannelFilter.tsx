"use client";

import { Button } from "@/components/ui/button";

interface ChannelFilterProps {
  selected: string;
  onChange: (channel: string) => void;
}

const CHANNELS = [
  { value: "", label: "All" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "email", label: "Email" },
];

export function ChannelFilter({ selected, onChange }: ChannelFilterProps) {
  return (
    <div className="flex gap-1">
      {CHANNELS.map((ch) => (
        <Button
          key={ch.value}
          size="sm"
          variant={selected === ch.value ? "default" : "outline"}
          onClick={() => onChange(ch.value)}
        >
          {ch.label}
        </Button>
      ))}
    </div>
  );
}
