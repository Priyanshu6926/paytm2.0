export type SoundboxStatus = 'idle' | 'playing';
export type SoundboxMode = 'wav' | 'chime' | 'silent';

export interface SoundboxState {
  status: SoundboxStatus;
  mode: SoundboxMode;
  announcement: string;
  sourceLabel: string;
  muted: boolean;
  isPaymentChime: boolean;
  hasLastClip: boolean;
}

export interface PlaySoundboxOptions {
  audioBase64?: string;
  announcement: string;
  sourceLabel?: string;
  isPaymentChime?: boolean;
}

type SoundboxListener = (state: SoundboxState) => void;

const DEFAULT_ANNOUNCEMENT = 'Paytm Soundbox Ready • Ganesh Provision Store';

let currentAudio: HTMLAudioElement | null = null;
let chimeTimer: ReturnType<typeof setTimeout> | null = null;
let lastPlayOptions: PlaySoundboxOptions | null = null;

let state: SoundboxState = {
  status: 'idle',
  mode: 'silent',
  announcement: DEFAULT_ANNOUNCEMENT,
  sourceLabel: 'Paytm Soundbox Chime',
  muted: false,
  isPaymentChime: false,
  hasLastClip: false,
};

const listeners = new Set<SoundboxListener>();

function notify() {
  const snapshot: SoundboxState = { ...state };
  listeners.forEach((listener) => listener(snapshot));
}

function clearChimeTimer() {
  if (chimeTimer !== null) {
    clearTimeout(chimeTimer);
    chimeTimer = null;
  }
}

export function getSoundboxState(): SoundboxState {
  return { ...state };
}

export function subscribeSoundbox(listener: SoundboxListener): () => void {
  listeners.add(listener);
  listener({ ...state });
  return () => {
    listeners.delete(listener);
  };
}

export function stopSoundboxAudio(): void {
  clearChimeTimer();
  if (currentAudio) {
    try {
      currentAudio.onended = null;
      currentAudio.onerror = null;
      currentAudio.pause();
      currentAudio.currentTime = 0;
    } catch {
      // Ignore audio teardown failures in constrained environments
    }
    currentAudio = null;
  }
  if (state.status !== 'idle') {
    state = { ...state, status: 'idle' };
    notify();
  }
}

export function toggleSoundboxMute(): boolean {
  const nextMuted = !state.muted;
  if (nextMuted) {
    stopSoundboxAudio();
  }
  state = { ...state, muted: nextMuted };
  notify();
  return nextMuted;
}

export function playPaytmChimeFallback(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  const AudioCtx =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

  if (!AudioCtx) {
    return false;
  }

  try {
    const ctx = new AudioCtx();
    if (ctx.state === 'suspended' && typeof ctx.resume === 'function') {
      void ctx.resume().catch(() => undefined);
    }

    const now = ctx.currentTime ?? 0;
    const notes = [
      { freq: 523.25, start: now, duration: 0.16 }, // C5
      { freq: 659.25, start: now + 0.13, duration: 0.24 }, // E5
    ];

    notes.forEach(({ freq, start, duration }) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, start);
      gain.gain.setValueAtTime(0.18, start);
      gain.gain.exponentialRampToValueAtTime(0.001, start + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + duration);
    });

    if (typeof ctx.close === 'function') {
      setTimeout(() => {
        void ctx.close().catch(() => undefined);
      }, 600);
    }
    return true;
  } catch {
    return false;
  }
}

export async function playSoundboxAudio(
  options: PlaySoundboxOptions,
): Promise<{ mode: SoundboxMode }> {
  stopSoundboxAudio();
  lastPlayOptions = { ...options };

  const sourceLabel =
    options.sourceLabel ??
    (options.audioBase64 && options.audioBase64.trim()
      ? 'Bulbul v3 TTS'
      : 'Paytm Soundbox Chime');

  if (state.muted) {
    state = {
      ...state,
      status: 'idle',
      mode: 'silent',
      announcement: options.announcement,
      sourceLabel,
      isPaymentChime: Boolean(options.isPaymentChime),
      hasLastClip: true,
    };
    notify();
    return { mode: 'silent' };
  }

  const cleanBase64 = options.audioBase64?.trim() ?? '';

  if (cleanBase64 && typeof Audio !== 'undefined') {
    try {
      const audio = new Audio(`data:audio/wav;base64,${cleanBase64}`);
      currentAudio = audio;

      state = {
        ...state,
        status: 'playing',
        mode: 'wav',
        announcement: options.announcement,
        sourceLabel,
        isPaymentChime: Boolean(options.isPaymentChime),
        hasLastClip: true,
      };
      notify();

      audio.onended = () => {
        if (currentAudio === audio) {
          currentAudio = null;
          state = { ...state, status: 'idle' };
          notify();
        }
      };

      audio.onerror = () => {
        if (currentAudio === audio) {
          currentAudio = null;
          const chimed = playPaytmChimeFallback();
          state = {
            ...state,
            status: chimed ? 'playing' : 'idle',
            mode: chimed ? 'chime' : 'silent',
            sourceLabel: chimed ? 'Paytm Soundbox Chime' : sourceLabel,
          };
          notify();
          if (chimed) {
            chimeTimer = setTimeout(() => {
              state = { ...state, status: 'idle' };
              notify();
            }, 450);
          }
        }
      };

      await audio.play();
      return { mode: 'wav' };
    } catch {
      currentAudio = null;
    }
  }

  const chimed = playPaytmChimeFallback();
  const mode: SoundboxMode = chimed ? 'chime' : 'silent';
  state = {
    ...state,
    status: chimed ? 'playing' : 'idle',
    mode,
    announcement: options.announcement,
    sourceLabel: chimed ? 'Paytm Soundbox Chime' : sourceLabel,
    isPaymentChime: Boolean(options.isPaymentChime),
    hasLastClip: true,
  };
  notify();

  if (chimed) {
    chimeTimer = setTimeout(() => {
      state = { ...state, status: 'idle' };
      notify();
    }, 450);
  }

  return { mode };
}

export async function replayLastSoundbox(): Promise<{ mode: SoundboxMode }> {
  if (!lastPlayOptions) {
    return playSoundboxAudio({
      announcement: state.announcement,
      sourceLabel: 'Paytm Soundbox Chime',
      isPaymentChime: true,
    });
  }
  return playSoundboxAudio(lastPlayOptions);
}
