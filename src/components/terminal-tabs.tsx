import { useState, useCallback } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Terminal } from "./terminal";
import { sshDisconnect } from "@/lib/commands";
import type { Host } from "@/lib/types";

interface Tab {
  hostId: number;
  label: string;
  sessionId: string;
}

interface Props {
  activeSessions: Map<number, Tab>;
  onCloseTab: (hostId: number) => void;
}

export function TerminalTabs({ activeSessions, onCloseTab }: Props) {
  const [activeTabId, setActiveTabId] = useState<number | null>(null);

  const tabs = Array.from(activeSessions.values());

  // When tabs change, auto-select the latest if none active
  if (tabs.length > 0 && (activeTabId === null || !activeSessions.has(activeTabId))) {
    setActiveTabId(tabs[tabs.length - 1].hostId);
  }

  const handleClose = useCallback(
    async (hostId: number) => {
      try {
        await sshDisconnect(hostId);
      } catch (e) {
        console.error("Disconnect error:", e);
      }
      onCloseTab(hostId);
      if (activeTabId === hostId) {
        const remaining = tabs.filter((t) => t.hostId !== hostId);
        setActiveTabId(remaining.length > 0 ? remaining[remaining.length - 1].hostId : null);
      }
    },
    [activeTabId, onCloseTab, tabs]
  );

  if (tabs.length === 0) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="text-center text-muted-foreground">
          <p className="text-lg font-medium">SSHive</p>
          <p className="text-sm mt-1">
            Double-click a host or right-click → Connect to start.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Tab bar */}
      <div className="flex items-center border-b bg-muted/40 px-1">
        <div className="flex flex-1 items-center gap-0 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.hostId}
              onClick={() => setActiveTabId(tab.hostId)}
              className={cn(
                "group flex items-center gap-1.5 border-r px-3 py-1.5 text-sm transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                activeTabId === tab.hostId
                  ? "bg-background text-foreground border-b-2 border-b-primary"
                  : "text-muted-foreground"
              )}
            >
              <span className="truncate max-w-40">{tab.label}</span>
              <span
                className="ml-0.5 rounded p-0.5 opacity-0 group-hover:opacity-100 hover:bg-muted"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClose(tab.hostId);
                }}
              >
                <X className="h-3 w-3" />
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Active terminal */}
      <div className="flex-1">
        {tabs.map((tab) => (
          <div
            key={tab.hostId}
            className={cn(
              "h-full w-full",
              activeTabId === tab.hostId ? "block" : "hidden"
            )}
          >
            <Terminal
              sessionId={tab.sessionId}
              onClose={() => handleClose(tab.hostId)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
