import { useState, useCallback } from "react";
import { ThemeProvider, useTheme } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { HostList } from "@/components/host-list";
import { HostDialog } from "@/components/host-dialog";
import { TerminalTabs } from "@/components/terminal-tabs";
import { TooltipProvider } from "@/components/ui/tooltip";
import { addHost, updateHost, sshConnect } from "@/lib/commands";
import type { Host } from "@/lib/types";

function AppInner() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingHost, setEditingHost] = useState<Host | null>(null);
  const [sessions, setSessions] = useState<Map<number, { hostId: number; label: string; sessionId: string }>>(new Map());
  const [statusText, setStatusText] = useState("Ready");

  const handleAdd = () => {
    setEditingHost(null);
    setDialogOpen(true);
  };

  const handleEdit = (host: Host) => {
    setEditingHost(host);
    setDialogOpen(true);
  };

  const handleSave = async (host: Host) => {
    try {
      if (host.id) {
        await updateHost(host.id, host);
      } else {
        await addHost(host);
      }
      setDialogOpen(false);
      setRefreshKey((k) => k + 1);
      setStatusText(host.id ? "Host updated" : "Host added");
    } catch (e) {
      console.error("Save failed:", e);
      setStatusText(`Error: ${e}`);
    }
  };

  const handleConnect = useCallback(
    async (host: Host) => {
      if (!host.id) return;
      const hostId = host.id;

      // If already connected, focus existing tab
      if (sessions.has(hostId)) {
        return; // TerminalTabs will auto-focus
      }

      setStatusText(`Connecting to ${host.name}...`);

      try {
        await sshConnect(hostId);
        setSessions((prev) => {
          const next = new Map(prev);
          next.set(hostId, {
            hostId,
            label: host.name,
            sessionId: String(hostId),
          });
          return next;
        });
        setStatusText(`Connected to ${host.name}`);
      } catch (e) {
        console.error("Connection failed:", e);
        setStatusText(`Connection failed: ${e}`);
      }
    },
    [sessions]
  );

  const handleCloseTab = useCallback((hostId: number) => {
    setSessions((prev) => {
      const next = new Map(prev);
      next.delete(hostId);
      return next;
    });
    setStatusText("Disconnected");
  }, []);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Header */}
      <header className="flex h-9 items-center justify-between border-b bg-background px-3 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">SSHive</span>
          <span className="text-xs text-muted-foreground hidden sm:inline">
            SSH Connection Manager
          </span>
        </div>
        <ThemeToggle />
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — host list */}
        <div className="w-60 shrink-0">
          <HostList
            onConnect={handleConnect}
            onEdit={handleEdit}
            onAdd={handleAdd}
            refreshKey={refreshKey}
          />
        </div>

        {/* Right — terminal area */}
        <div className="flex-1 overflow-hidden">
          <TerminalTabs
            activeSessions={sessions}
            onCloseTab={handleCloseTab}
          />
        </div>
      </div>

      {/* Status bar */}
      <footer className="flex h-6 items-center border-t bg-muted/40 px-3 shrink-0">
        <span className="text-xs text-muted-foreground">{statusText}</span>
      </footer>

      {/* Host dialog */}
      <HostDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSave={handleSave}
        editHost={editingHost}
      />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <TooltipProvider>
        <AppInner />
      </TooltipProvider>
    </ThemeProvider>
  );
}
