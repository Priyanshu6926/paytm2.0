import { useEffect, useState } from 'react';
import { RotateCcw, Volume2, VolumeX } from 'lucide-react';
import {
  getSoundboxState,
  replayLastSoundbox,
  subscribeSoundbox,
  toggleSoundboxMute,
  type SoundboxState,
} from '../utils/soundboxAudio';

export function SoundboxBanner() {
  const [soundbox, setSoundbox] = useState<SoundboxState>(() => getSoundboxState());

  useEffect(() => {
    return subscribeSoundbox(setSoundbox);
  }, []);

  const isPlaying = soundbox.status === 'playing';
  const barDelays = ['0ms', '120ms', '240ms', '80ms', '180ms'];

  return (
    <section
      aria-label="Paytm Soundbox Simulator"
      className={`rounded-2xl bg-gradient-to-r from-paytm-navy to-paytm-navyDark text-white px-3 py-2.5 shadow-sm transition-all ${
        isPlaying
          ? 'ring-2 ring-paytm-cyan shadow-[0_0_16px_rgba(0,186,242,0.35)]'
          : 'border border-paytm-navy/20'
      }`}
    >
      <div className="flex items-center justify-between gap-2.5">
        {/* Live 5-Bar Equalizer */}
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            aria-hidden="true"
            className="w-8 h-8 rounded-xl bg-white/10 border border-white/10 flex items-end justify-center gap-[2px] p-1.5 shrink-0"
          >
            {barDelays.map((delay, idx) => (
              <span
                key={idx}
                style={{ animationDelay: delay }}
                className={`w-[3px] rounded-full bg-paytm-cyan transition-all ${
                  isPlaying ? 'h-full animate-soundbox-bar' : 'h-1.5 opacity-60'
                }`}
              />
            ))}
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-paytm-cyan">
                Paytm Soundbox
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 text-white/85 font-medium truncate">
                {soundbox.sourceLabel}
              </span>
            </div>
            <p className="text-xs font-medium text-white truncate mt-0.5">
              {soundbox.announcement}
            </p>
          </div>
        </div>

        {/* Replay & Mute Controls */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => void replayLastSoundbox()}
            aria-label="Replay Soundbox announcement"
            title="Replay announcement"
            className="min-h-[36px] min-w-[36px] rounded-xl bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => toggleSoundboxMute()}
            aria-label={soundbox.muted ? 'Unmute Soundbox' : 'Mute Soundbox'}
            title={soundbox.muted ? 'Unmute Soundbox' : 'Mute Soundbox'}
            className={`min-h-[36px] min-w-[36px] rounded-xl flex items-center justify-center transition-colors ${
              soundbox.muted
                ? 'bg-rose-500/25 text-rose-200 hover:bg-rose-500/35'
                : 'bg-white/10 hover:bg-white/20 text-white'
            }`}
          >
            {soundbox.muted ? (
              <VolumeX className="w-4 h-4" />
            ) : (
              <Volume2 className="w-4 h-4 text-paytm-cyan" />
            )}
          </button>
        </div>
      </div>
    </section>
  );
}
