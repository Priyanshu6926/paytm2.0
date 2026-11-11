import { createElement } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { WhyAmISeeingThis } from '../../components/WhyAmISeeingThis';
import {
  getSoundboxState,
  playSoundboxAudio,
  stopSoundboxAudio,
  subscribeSoundbox,
  toggleSoundboxMute,
} from '../soundboxAudio';

describe('soundboxAudio', () => {
  const createdAudios: Array<{
    src: string;
    play: ReturnType<typeof vi.fn>;
    pause: ReturnType<typeof vi.fn>;
    onended: (() => void) | null;
    onerror: (() => void) | null;
    currentTime: number;
  }> = [];

  const createdOscillators: Array<{
    frequency: { setValueAtTime: ReturnType<typeof vi.fn> };
    connect: ReturnType<typeof vi.fn>;
    start: ReturnType<typeof vi.fn>;
    stop: ReturnType<typeof vi.fn>;
    type: string;
  }> = [];

  beforeEach(() => {
    createdAudios.length = 0;
    createdOscillators.length = 0;
    stopSoundboxAudio();
    if (getSoundboxState().muted) {
      toggleSoundboxMute();
    }

    class MockAudio {
      src: string;
      currentTime = 0;
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      play = vi.fn().mockResolvedValue(undefined);
      pause = vi.fn();

      constructor(src = '') {
        this.src = src;
        createdAudios.push(this);
      }
    }

    class MockAudioContext {
      currentTime = 0;
      destination = {};
      state = 'running';
      resume = vi.fn().mockResolvedValue(undefined);
      close = vi.fn().mockResolvedValue(undefined);
      createOscillator = vi.fn(() => {
        const osc = {
          type: 'sine',
          frequency: { setValueAtTime: vi.fn() },
          connect: vi.fn(),
          start: vi.fn(),
          stop: vi.fn(),
        };
        createdOscillators.push(osc);
        return osc;
      });
      createGain = vi.fn(() => ({
        gain: {
          setValueAtTime: vi.fn(),
          exponentialRampToValueAtTime: vi.fn(),
        },
        connect: vi.fn(),
      }));
    }

    vi.stubGlobal('Audio', MockAudio);
    vi.stubGlobal('AudioContext', MockAudioContext);
  });

  afterEach(() => {
    stopSoundboxAudio();
    vi.unstubAllGlobals();
  });

  it('plays base64 WAV audio via data:audio/wav;base64,... and notifies listeners', async () => {
    const statuses: string[] = [];
    const unsubscribe = subscribeSoundbox((state) => {
      statuses.push(state.status);
    });

    const result = await playSoundboxAudio({
      audioBase64: 'UklGRgAA',
      announcement: 'Paytm par 650 rupaye prapt hue',
      sourceLabel: 'Bulbul v3 TTS',
    });

    expect(result.mode).toBe('wav');
    expect(createdAudios).toHaveLength(1);
    expect(createdAudios[0].src).toBe('data:audio/wav;base64,UklGRgAA');
    expect(createdAudios[0].play).toHaveBeenCalledTimes(1);
    expect(statuses).toContain('playing');

    createdAudios[0].onended?.();
    expect(getSoundboxState().status).toBe('idle');
    unsubscribe();
  });

  it('falls back to WebAudio dual-tone chime (523.25Hz + 659.25Hz) when audio is empty or blocked', async () => {
    const emptyResult = await playSoundboxAudio({
      audioBase64: '',
      announcement: 'Paytm par 200 rupaye prapt hue',
      isPaymentChime: true,
    });

    expect(emptyResult.mode).toBe('chime');
    expect(createdOscillators.length).toBeGreaterThanOrEqual(2);
    const freqsAfterEmpty = createdOscillators.map(
      (osc) => osc.frequency.setValueAtTime.mock.calls[0]?.[0],
    );
    expect(freqsAfterEmpty).toContain(523.25);
    expect(freqsAfterEmpty).toContain(659.25);

    createdOscillators.length = 0;
    class BlockedAudio {
      src: string;
      currentTime = 0;
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      play = vi.fn().mockRejectedValue(new Error('Autoplay blocked'));
      pause = vi.fn();
      constructor(src = '') {
        this.src = src;
      }
    }
    vi.stubGlobal('Audio', BlockedAudio);

    const blockedResult = await playSoundboxAudio({
      audioBase64: 'UklGRgAA',
      announcement: 'Settlement explained',
    });

    expect(blockedResult.mode).toBe('chime');
    const freqsAfterBlocked = createdOscillators.map(
      (osc) => osc.frequency.setValueAtTime.mock.calls[0]?.[0],
    );
    expect(freqsAfterBlocked).toContain(523.25);
    expect(freqsAfterBlocked).toContain(659.25);
  });

  it('stops previous audio clip before starting a new clip to prevent overlap', async () => {
    await playSoundboxAudio({
      audioBase64: 'AAAA',
      announcement: 'First clip',
    });
    await playSoundboxAudio({
      audioBase64: 'BBBB',
      announcement: 'Second clip',
    });

    expect(createdAudios).toHaveLength(2);
    expect(createdAudios[0].pause).toHaveBeenCalledTimes(1);
    expect(createdAudios[1].play).toHaveBeenCalledTimes(1);
    expect(getSoundboxState().announcement).toBe('Second clip');
  });
});

describe('WhyAmISeeingThis', () => {
  it('renders collapsed by default and expands/collapses formula, source, delta, and evidence JSON', () => {
    render(
      createElement(WhyAmISeeingThis, {
        formula: '6450 - (450 + 125 + 60) = 5815',
        source: 'Deterministic SQLite Settlement Engine',
        beforeLabel: 'Gross ₹6,450',
        afterLabel: 'Net ₹5,815',
        evidence: { gross_qr_collections: 6450, net_settled_to_bank: 5815 },
      }),
    );

    const toggleButton = screen.getByRole('button', { name: /why am i seeing this\?/i });
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    expect(toggleButton.className).toContain('min-h-[44px]');
    expect(screen.queryByText(/6450 - \(450 \+ 125 \+ 60\) = 5815/)).not.toBeInTheDocument();

    fireEvent.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText(/6450 - \(450 \+ 125 \+ 60\) = 5815/)).toBeInTheDocument();
    expect(screen.getByText(/Deterministic SQLite Settlement Engine/)).toBeInTheDocument();
    expect(screen.getByText(/Gross ₹6,450/)).toBeInTheDocument();
    expect(screen.getByText(/Net ₹5,815/)).toBeInTheDocument();
    expect(screen.getByText(/"net_settled_to_bank": 5815/)).toBeInTheDocument();

    fireEvent.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/6450 - \(450 \+ 125 \+ 60\) = 5815/)).not.toBeInTheDocument();
  });
});
