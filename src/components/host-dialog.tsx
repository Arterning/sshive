import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Host } from "@/lib/types";

const emptyHost: Host = {
  id: null,
  name: "",
  host: "",
  port: 22,
  username: "",
  password: "",
  auth_type: "password",
  private_key_path: "",
  description: "",
  created_at: "",
  updated_at: "",
};

interface Props {
  open: boolean;
  onClose: () => void;
  onSave: (host: Host) => void;
  editHost?: Host | null;
}

export function HostDialog({ open, onClose, onSave, editHost }: Props) {
  const [host, setHost] = useState<Host>(emptyHost);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setHost(editHost ? { ...editHost } : { ...emptyHost });
      setErrors({});
    }
  }, [open, editHost]);

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!host.name.trim()) e.name = "Name is required";
    if (!host.host.trim()) e.host = "Host is required";
    if (!host.username.trim()) e.username = "Username is required";
    if (host.auth_type === "password" && !host.password) {
      e.password = "Password is required";
    }
    if (host.auth_type === "key" && !host.private_key_path.trim()) {
      e.private_key_path = "Private key path is required";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSave = () => {
    if (!validate()) return;
    onSave({ ...host });
  };

  const update = (field: keyof Host, value: string | number) => {
    setHost((h) => ({ ...h, [field]: value }));
    setErrors((e) => {
      const next = { ...e };
      delete next[field];
      return next;
    });
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {editHost ? "Edit Host" : "Add Host"}
          </DialogTitle>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-1.5">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              value={host.name}
              onChange={(e) => update("name", e.target.value)}
              placeholder="My Server"
            />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name}</p>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2 grid gap-1.5">
              <Label htmlFor="host">Host *</Label>
              <Input
                id="host"
                value={host.host}
                onChange={(e) => update("host", e.target.value)}
                placeholder="192.168.1.1"
              />
              {errors.host && (
                <p className="text-xs text-destructive">{errors.host}</p>
              )}
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="port">Port</Label>
              <Input
                id="port"
                type="number"
                value={host.port}
                onChange={(e) => update("port", parseInt(e.target.value) || 22)}
                min={1}
                max={65535}
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="username">Username *</Label>
            <Input
              id="username"
              value={host.username}
              onChange={(e) => update("username", e.target.value)}
              placeholder="root"
            />
            {errors.username && (
              <p className="text-xs text-destructive">{errors.username}</p>
            )}
          </div>

          <div className="grid gap-1.5">
            <Label>Auth Type</Label>
            <Select
              value={host.auth_type}
              onValueChange={(v) => update("auth_type", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="password">Password</SelectItem>
                <SelectItem value="key">Private Key</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {host.auth_type === "password" ? (
            <div className="grid gap-1.5">
              <Label htmlFor="password">Password *</Label>
              <Input
                id="password"
                type="password"
                value={host.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="••••••••"
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password}</p>
              )}
            </div>
          ) : (
            <div className="grid gap-1.5">
              <Label htmlFor="keypath">Private Key Path *</Label>
              <Input
                id="keypath"
                value={host.private_key_path}
                onChange={(e) => update("private_key_path", e.target.value)}
                placeholder="C:\\Users\\...\\id_rsa"
              />
              {errors.private_key_path && (
                <p className="text-xs text-destructive">
                  {errors.private_key_path}
                </p>
              )}
            </div>
          )}

          <div className="grid gap-1.5">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={host.description}
              onChange={(e) => update("description", e.target.value)}
              placeholder="Optional notes..."
            />
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            {editHost ? "Save" : "Add"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
