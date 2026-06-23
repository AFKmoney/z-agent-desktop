"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { buildWsUrl, agentApi, type AgentStatus, type LogEntry } from "@/lib/agent-api";

type ProgressEvent =
  | { event: "task_start"; task_id: string; request: string }
  | { event: "plan_ready"; task_id: string; plan: unknown }
  | { event: "step_progress"; task_id: string; current_step: number; total_steps: number; step: unknown; result: unknown }
  | { event: "task_end"; task_id: string; result: unknown };

interface UseAgentResult {
  status: AgentStatus | null;
  logs: LogEntry[];
  progress: ProgressEvent[];
  connected: boolean;
  refresh: () => void;
}

export function useAgent(): UseAgentResult {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [connected, setConnected] = useState(false);

  const logWsRef = useRef<WebSocket | null>(null);
  const progressWsRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await agentApi.status();
      setStatus(s);
    } catch (e) {
      // API not reachable (backend offline) — show stopped state
      setStatus((prev) => prev ?? {
        state: "stopped",
        current_task: null,
        queue_size: 0,
        memory: null,
        uptime_s: 0,
      });
    }
  }, []);

  // Poll status every 3 seconds (fallback if WS not connected)
  useEffect(() => {
    let cancelled = false;
    const doRefresh = async () => {
      await refresh();
      if (cancelled) return;
    };
    doRefresh();
    pollIntervalRef.current = setInterval(doRefresh, 3000);
    return () => {
      cancelled = true;
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [refresh]);

  // WebSocket for logs
  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const connect = () => {
      if (closed) return;
      try {
        const ws = new WebSocket(buildWsUrl("/ws/logs"));
        logWsRef.current = ws;

        ws.onopen = () => {
          setConnected(true);
          console.log("[Z.AGENT] Logs WS connected");
        };

        ws.onmessage = (ev) => {
          try {
            const entry: LogEntry = JSON.parse(ev.data);
            setLogs((prev) => [...prev.slice(-499), entry]);
          } catch (e) {
            // ignore non-JSON
          }
        };

        ws.onclose = () => {
          setConnected(false);
          if (!closed) {
            reconnectTimer = setTimeout(connect, 3000);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (e) {
        reconnectTimer = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (logWsRef.current) {
        logWsRef.current.close();
        logWsRef.current = null;
      }
    };
  }, []);

  // WebSocket for progress events
  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const connect = () => {
      if (closed) return;
      try {
        const ws = new WebSocket(buildWsUrl("/ws/progress"));
        progressWsRef.current = ws;

        ws.onmessage = (ev) => {
          try {
            const event: ProgressEvent = JSON.parse(ev.data);
            setProgress((prev) => [...prev.slice(-99), event]);
            // Trigger status refresh on key events
            if (event.event === "task_end" || event.event === "task_start") {
              setTimeout(refresh, 100);
            }
          } catch (e) {
            // ignore
          }
        };

        ws.onclose = () => {
          if (!closed) {
            reconnectTimer = setTimeout(connect, 3000);
          }
        };

        ws.onerror = () => ws.close();
      } catch (e) {
        reconnectTimer = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (progressWsRef.current) {
        progressWsRef.current.close();
        progressWsRef.current = null;
      }
    };
  }, [refresh]);

  return { status, logs, progress, connected, refresh };
}
