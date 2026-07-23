import { useEffect, useRef, useCallback } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebglAddon } from "@xterm/addon-webgl";
import { listen } from "@tauri-apps/api/event";
import { sshSend } from "@/lib/commands";
import type { SshDataEvent, SshClosedEvent } from "@/lib/types";
import "@xterm/xterm/css/xterm.css";

interface Props {
  sessionId: string;
  onClose?: () => void;
}

export function Terminal({ sessionId, onClose }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const unlistenRef = useRef<(() => void)[]>([]);

  // Initialize xterm.js
  const initTerminal = useCallback(() => {
    if (!containerRef.current || xtermRef.current) return;

    const term = new XTerm({
      cursorBlink: true,
      cursorStyle: "bar",
      fontSize: 14,
      fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
      theme: {
        background: "#1e1e1e",
        foreground: "#d4d4d4",
        cursor: "#ffffff",
        selectionBackground: "#264f78",
        black: "#000000",
        red: "#cd3131",
        green: "#0dbc79",
        yellow: "#e5e510",
        blue: "#2472c8",
        magenta: "#bc3fbc",
        cyan: "#11a8cd",
        white: "#e5e5e5",
        brightBlack: "#666666",
        brightRed: "#f14c4c",
        brightGreen: "#23d18b",
        brightYellow: "#f5f543",
        brightBlue: "#3b8eea",
        brightMagenta: "#d670d6",
        brightCyan: "#29b8db",
        brightWhite: "#e5e5e5",
      },
      allowTransparency: false,
      disableStdin: false,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);

    // Try WebGL, fall back to canvas
    try {
      const webglAddon = new WebglAddon();
      webglAddon.onContextLoss(() => {
        webglAddon.dispose();
      });
      term.loadAddon(webglAddon);
    } catch {
      // WebGL not available, use default canvas renderer
    }

    term.open(containerRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;
  }, []);

  // Listen for SSH data events
  useEffect(() => {
    initTerminal();

    const unlisteners: (() => void)[] = [];

    // Listen for data from the SSH server
    listen<SshDataEvent>("ssh-data", (event) => {
      if (event.payload.session_id === sessionId) {
        try {
          const bytes = Uint8Array.from(atob(event.payload.data), (c) =>
            c.charCodeAt(0)
          );
          xtermRef.current?.write(bytes);
        } catch (e) {
          console.error("Failed to decode SSH data:", e);
        }
      }
    }).then((fn) => unlisteners.push(fn));

    // Listen for close events
    listen<SshClosedEvent>("ssh-closed", (event) => {
      if (event.payload.session_id === sessionId) {
        xtermRef.current?.writeln("\r\n\x1b[33m[Connection closed]\x1b[0m");
        onClose?.();
      }
    }).then((fn) => unlisteners.push(fn));

    unlistenRef.current = unlisteners;

    return () => {
      unlisteners.forEach((fn) => fn());
    };
  }, [sessionId, initTerminal, onClose]);

  // Forward keystrokes to SSH
  useEffect(() => {
    const term = xtermRef.current;
    if (!term) return;

    const disposable = term.onData((data) => {
      // Local echo (xterm.js v6 no longer echoes by default without a PTY)
      term.write(data);
      // Forward to SSH
      const bytes = new TextEncoder().encode(data);
      sshSend(parseInt(sessionId), bytes).catch(console.error);
    });

    return () => disposable.dispose();
  }, [sessionId]);

  // Handle resize
  useEffect(() => {
    const fitAddon = fitAddonRef.current;
    if (!fitAddon) return;

    const handleResize = () => {
      fitAddon.fit();
    };

    const observer = new ResizeObserver(handleResize);
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    window.addEventListener("resize", handleResize);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      xtermRef.current?.dispose();
      xtermRef.current = null;
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="h-full w-full"
      style={{ background: "#1e1e1e" }}
    />
  );
}
