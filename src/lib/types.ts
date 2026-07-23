export interface Host {
  id: number | null;
  name: string;
  host: string;
  port: number;
  username: string;
  password: string;
  auth_type: "password" | "key";
  private_key_path: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface SshDataEvent {
  session_id: string;
  data: string; // base64-encoded
}

export interface SshClosedEvent {
  session_id: string;
}

export interface SshErrorEvent {
  session_id: string;
  error: string;
}
