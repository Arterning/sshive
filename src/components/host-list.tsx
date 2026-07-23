import { useEffect, useState, useCallback } from "react";
import { Search, Plus, Trash2, Pencil, MonitorPlay } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { cn } from "@/lib/utils";
import { getHosts, searchHosts, deleteHost } from "@/lib/commands";
import type { Host } from "@/lib/types";

interface Props {
  onConnect: (host: Host) => void;
  onEdit: (host: Host) => void;
  onAdd: () => void;
  refreshKey: number;
}

export function HostList({ onConnect, onEdit, onAdd, refreshKey }: Props) {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [keyword, setKeyword] = useState("");

  const loadHosts = useCallback(async () => {
    try {
      const list = keyword
        ? await searchHosts(keyword)
        : await getHosts();
      setHosts(list);
    } catch (e) {
      console.error("Failed to load hosts:", e);
    }
  }, [keyword]);

  useEffect(() => {
    loadHosts();
  }, [loadHosts, refreshKey]);

  const handleDelete = async (host: Host) => {
    if (!host.id) return;
    try {
      await deleteHost(host.id);
      loadHosts();
    } catch (e) {
      console.error("Failed to delete host:", e);
    }
  };

  return (
    <div className="flex h-full flex-col border-r bg-background">
      {/* Search + Add bar */}
      <div className="flex items-center gap-1.5 p-2 border-b">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className="h-8 pl-7 text-sm"
          />
        </div>
        <Button size="icon" variant="ghost" className="h-8 w-8" onClick={onAdd}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Host list */}
      <ScrollArea className="flex-1">
        <div className="p-1">
          {hosts.length === 0 && (
            <p className="px-3 py-6 text-center text-xs text-muted-foreground">
              No hosts found
            </p>
          )}
          {hosts.map((host) => (
            <ContextMenu key={host.id}>
              <ContextMenuTrigger asChild>
                <button
                  className={cn(
                    "w-full rounded-md px-3 py-2 text-left text-sm transition-colors",
                    "hover:bg-accent hover:text-accent-foreground",
                    "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  )}
                  onDoubleClick={() => onConnect(host)}
                  title={`${host.name} (${host.username}@${host.host}:${host.port})`}
                >
                  <div className="font-medium truncate">{host.name}</div>
                  <div className="text-xs text-muted-foreground truncate">
                    {host.username}@{host.host}:{host.port}
                  </div>
                </button>
              </ContextMenuTrigger>
              <ContextMenuContent className="w-40">
                <ContextMenuItem onClick={() => onConnect(host)}>
                  <MonitorPlay className="mr-2 h-3.5 w-3.5" />
                  Connect
                </ContextMenuItem>
                <ContextMenuItem onClick={() => onEdit(host)}>
                  <Pencil className="mr-2 h-3.5 w-3.5" />
                  Edit
                </ContextMenuItem>
                <ContextMenuSeparator />
                <ContextMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => handleDelete(host)}
                >
                  <Trash2 className="mr-2 h-3.5 w-3.5" />
                  Delete
                </ContextMenuItem>
              </ContextMenuContent>
            </ContextMenu>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
