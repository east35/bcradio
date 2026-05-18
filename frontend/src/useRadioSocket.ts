import { useEffect, useMemo, useRef, useState } from "react";
import { fallbackState, RadioState } from "./types";

const keyMap: Record<string, string> = {
  ArrowLeft: "tune_left",
  ArrowRight: "tune_right",
  Enter: "tune_press",
  ArrowUp: "volume_up",
  ArrowDown: "volume_down",
  " ": "volume_press",
  p: "power_press",
  P: "power_press"
};

export function useRadioSocket() {
  const [state, setState] = useState<RadioState>(fallbackState);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;

    const connect = () => {
      if (cancelled) return;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);
      socketRef.current = socket;

      socket.addEventListener("open", () => setConnected(true));
      socket.addEventListener("message", (event) => {
        setState(JSON.parse(event.data));
      });
      const scheduleReconnect = () => {
        if (cancelled) return;
        setConnected(false);
        socketRef.current = null;
        window.clearTimeout(retryTimer);
        retryTimer = window.setTimeout(connect, 1000);
      };
      socket.addEventListener("close", scheduleReconnect);
      socket.addEventListener("error", scheduleReconnect);
    };

    connect();

    return () => {
      cancelled = true;
      window.clearTimeout(retryTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const radioEvent = keyMap[event.key];
      if (!radioEvent) return;
      event.preventDefault();
      socketRef.current?.send(JSON.stringify({ event: radioEvent }));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return useMemo(() => ({ state, connected }), [state, connected]);
}

