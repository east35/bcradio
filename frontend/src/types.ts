export type Mode =
  | "idle"
  | "station_select"
  | "playback"
  | "paused"
  | "no_connection"
  | "soft_off_pending"
  | "off";

export type ConnectionStatus = "online" | "offline_cached" | "offline_unavailable";
export type PlaybackStatus = "playing" | "paused" | "fading_in" | "fading_out" | "stopped";
export type Theme = "light" | "dark";

export interface RadioState {
  mode: Mode;
  genre: string;
  showTitle: string;
  showDate: string;
  artistName: string;
  trackTitle: string;
  albumArtUrl: string;
  trackIndex: number;
  trackTotal: number;
  elapsedSeconds: number;
  durationSeconds: number;
  volume: number;
  volumeOverlayVisible: boolean;
  connectionStatus: ConnectionStatus;
  errorMessage: string;
  playbackStatus: PlaybackStatus;
  theme: Theme;
}

export const fallbackState: RadioState = {
  mode: "idle",
  genre: "Indie",
  showTitle: "Indie Radio",
  showDate: "Demo",
  artistName: "Bandcamp Radio",
  trackTitle: "signal check",
  albumArtUrl: "/assets/album art fallback/Art=No.png",
  trackIndex: 0,
  trackTotal: 2,
  elapsedSeconds: 0,
  durationSeconds: 180,
  volume: 70,
  volumeOverlayVisible: false,
  connectionStatus: "online",
  errorMessage: "",
  playbackStatus: "stopped",
  theme: "light"
};

