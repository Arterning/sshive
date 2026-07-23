import { invoke } from "@tauri-apps/api/core";
import type { Host } from "./types";

export async function getHosts(): Promise<Host[]> {
  return invoke("get_all_hosts");
}

export async function searchHosts(keyword: string): Promise<Host[]> {
  return invoke("search_hosts", { keyword });
}

export async function addHost(host: Host): Promise<Host> {
  return invoke("add_host", { host });
}

export async function updateHost(id: number, host: Host): Promise<void> {
  return invoke("update_host", { id, host });
}

export async function deleteHost(id: number): Promise<void> {
  return invoke("delete_host", { id });
}

export async function sshConnect(hostId: number): Promise<void> {
  return invoke("ssh_connect", { hostId });
}

export async function sshSend(hostId: number, data: Uint8Array): Promise<void> {
  return invoke("ssh_send", { hostId, data: Array.from(data) });
}

export async function sshDisconnect(hostId: number): Promise<void> {
  return invoke("ssh_disconnect", { hostId });
}
