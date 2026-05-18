import React from "react";
import ReactDOM from "react-dom/client";
import { useRadioSocket } from "./useRadioSocket";
import { RadioState } from "./types";
import "./styles.css";

const genres = ["Electronic", "Selects", "Hip-Hop", "Indie", "Metal", "Games"];

function formatTime(seconds: number) {
  const safe = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(safe / 60);
  const secs = String(safe % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}

function Clock() {
  const [now, setNow] = React.useState(new Date());
  React.useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="clock">
      {now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
    </div>
  );
}

function StationSelect({ state }: { state: RadioState }) {
  const len = genres.length;
  const target = Math.max(0, genres.indexOf(state.genre));
  // Extended list of 3 copies; middle copy is [len, 2*len). cursor is the absolute index.
  const [cursor, setCursor] = React.useState(len + target);
  const [animate, setAnimate] = React.useState(true);
  const prevTarget = React.useRef(target);

  React.useEffect(() => {
    if (target === prevTarget.current) return;
    const half = Math.floor(len / 2);
    const diff = ((target - prevTarget.current + len + half) % len) - half;
    setAnimate(true);
    setCursor((c) => c + diff);
    prevTarget.current = target;
  }, [target, len]);

  // After animation, snap back into the middle copy without transition.
  React.useEffect(() => {
    if (cursor >= len && cursor < 2 * len) return;
    const t = window.setTimeout(() => {
      setAnimate(false);
      setCursor((c) => len + (((c % len) + len) % len));
    }, 340);
    return () => window.clearTimeout(t);
  }, [cursor, len]);

  React.useEffect(() => {
    if (animate) return;
    const id = requestAnimationFrame(() => setAnimate(true));
    return () => cancelAnimationFrame(id);
  }, [animate]);

  const containerRef = React.useRef<HTMLDivElement>(null);
  const itemRefs = React.useRef<(HTMLSpanElement | null)[]>([]);
  const [offset, setOffset] = React.useState(0);

  React.useLayoutEffect(() => {
    const container = containerRef.current;
    const active = itemRefs.current[cursor];
    if (!container || !active) return;
    const recompute = () => {
      setOffset(container.clientWidth / 2 - (active.offsetLeft + active.offsetWidth / 2));
    };
    recompute();
    const fontsReady = (document as Document & { fonts?: { ready: Promise<unknown> } }).fonts?.ready;
    if (fontsReady) fontsReady.then(recompute);
  }, [cursor]);

  const items = Array.from({ length: 3 * len }, (_, i) => ({
    key: i,
    label: genres[i % len],
    isActive: i === cursor
  }));

  return (
    <div className="station-select" ref={containerRef}>
      <div
        className="station-track"
        style={{
          transform: `translateX(${offset}px)`,
          transition: animate ? "transform 320ms ease" : "none"
        }}
      >
        {items.map((it, i) => (
          <span
            key={it.key}
            ref={(el) => {
              itemRefs.current[i] = el;
            }}
            className="station-item"
            style={{ opacity: it.isActive ? 1 : 0.2 }}
          >
            {it.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function TrackTitle({ text }: { text: string }) {
  return <div className="pb-title">{text}</div>;
}

function Playback({ state }: { state: RadioState }) {
  const progress =
    state.durationSeconds > 0 ? Math.min(100, (state.elapsedSeconds / state.durationSeconds) * 100) : 0;
  const isPaused = state.mode === "paused" || state.playbackStatus === "paused";
  const trackNum = Math.min(state.trackIndex + 1, state.trackTotal || 1);
  return (
    <div className="playback">
      <div className="pb-top">
        <span className="pb-meta">
          {state.genre} / {state.showTitle} ({state.showDate})
        </span>
        <img
          className="pb-status-icon"
          src={isPaused ? "/assets/icons/paused.svg" : "/assets/icons/playing.svg"}
          alt={isPaused ? "paused" : "playing"}
        />
      </div>

      <div className="pb-middle">
        <div className="pb-art">
          <img src={state.albumArtUrl} alt="" />
          <img className="pb-art-pattern" src="/assets/icons/album_pattern.svg" alt="" aria-hidden="true" />
        </div>
        <div className="pb-track">
          <TrackTitle text={state.trackTitle || state.showTitle} />
          <div className="pb-artist">{state.artistName}</div>
        </div>
      </div>

      <div className="pb-bottom">
        <span className="pb-counter">
          {trackNum}/{state.trackTotal || 1}
        </span>
        <span className="pb-elapsed">{formatTime(state.elapsedSeconds)}</span>
        <div className={`pb-progress ${isPaused ? "is-paused" : ""}`}>
          {isPaused ? (
            <>
              <div className="pb-progress-line-left" style={{ width: `calc(${progress}% - 2pt - 1px)` }} />
              <div className="pb-progress-line-right" style={{ width: `calc(${100 - progress}% - 2pt - 1px)` }} />
              <div className="pb-progress-tick" style={{ left: `${progress}%` }} />
            </>
          ) : (
            <>
              <div className="pb-progress-fill" style={{ width: `${progress}%` }} />
              <div className="pb-progress-line-right" style={{ width: `calc(${100 - progress}% - 2pt)` }} />
            </>
          )}
        </div>
        <span className="pb-duration">{formatTime(state.durationSeconds)}</span>
      </div>
    </div>
  );
}

function NoConnection() {
  return (
    <div className="no-connection">
      <img src="/assets/icons/no_wifi.svg" alt="no connection" />
    </div>
  );
}

function VolumeOverlay({ volume }: { volume: number }) {
  return (
    <div className="volume-toast">
      <span>VOL</span>
      <div>
        <i style={{ width: `${volume}%` }} />
      </div>
      <strong>{volume}</strong>
    </div>
  );
}

function Screen() {
  const { state, connected } = useRadioSocket();
  const offline = state.connectionStatus !== "online" || !connected;
  const showError = state.mode === "no_connection" || state.mode === "off" || offline;
  return (
    <main className={`screen ${state.theme} mode-${state.mode}`}>
      <div className="bezel-shadow" />
      {state.mode === "idle" && !showError ? <Clock /> : null}
      {state.mode === "station_select" && !showError ? <StationSelect state={state} /> : null}
      {(state.mode === "playback" || state.mode === "paused" || state.mode === "soft_off_pending") && !showError ? (
        <Playback state={state} />
      ) : null}
      {showError ? <NoConnection /> : null}
      {state.volumeOverlayVisible ? <VolumeOverlay volume={state.volume} /> : null}
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Screen />
  </React.StrictMode>
);
