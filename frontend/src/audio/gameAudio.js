const STORAGE_KEY = 'adaptation-game-audio-muted'

const SCENES = {
  entry: {
    interval: 1400,
    notes: [57, 64, 60, 67, 62, 69, 64, 67],
    bass: [45, 48, 50, 52],
    wave: 'sine', level: 0.042, duration: 1.8,
  },
  planning: {
    interval: 900,
    notes: [60, 64, 67, 69, 67, 64, 62, 67],
    bass: [48, 45, 50, 43],
    wave: 'triangle', level: 0.038, duration: 1.15,
  },
  reflection: {
    interval: 1250,
    notes: [62, 65, 69, 67, 64, 67, 60, 64],
    bass: [43, 46, 41, 48],
    wave: 'sine', level: 0.036, duration: 1.55,
  },
  danger: {
    interval: 650,
    notes: [50, 51, 57, 56, 50, 58, 51, 55],
    bass: [38, 39, 38, 34],
    wave: 'triangle', level: 0.034, duration: 0.82,
  },
  hopeful: {
    interval: 820,
    notes: [60, 64, 67, 72, 69, 67, 64, 69],
    bass: [48, 53, 45, 55],
    wave: 'sine', level: 0.042, duration: 1.1,
  },
  finale: {
    interval: 760,
    notes: [60, 64, 67, 72, 76, 72, 69, 67],
    bass: [48, 53, 45, 55],
    wave: 'triangle', level: 0.045, duration: 1.2,
  },
}

export function sceneForPhase(phase, event = {}) {
  if (phase === 'entry' || phase === 'finished') return 'entry'
  if (phase === 'game') return 'planning'
  if (phase === 'consequence') return isPositiveEvent(event) ? 'hopeful' : 'danger'
  if (phase === 'completion' || phase === 'ending') return 'finale'
  return 'reflection'
}

export function isPositiveEvent(event = {}) {
  if (event.category === 'policy_effect') return true
  const id = String(event.id ?? event.key ?? '').toLowerCase()
  return /(completed|improved|avoided|effect|started|high$)/.test(id)
    && !/(damage|critical|low|risk|pressure|unmanaged)/.test(id)
}

function readInitialMuted() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

function midiToFrequency(note) {
  return 440 * (2 ** ((note - 69) / 12))
}

class GameAudioEngine {
  constructor() {
    this.context = null
    this.master = null
    this.musicBus = null
    this.sfxBus = null
    this.scene = 'entry'
    this.step = 0
    this.timer = null
    this.muted = typeof window === 'undefined' ? false : readInitialMuted()
    this.listeners = new Set()
  }

  subscribe(listener) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  snapshot() {
    return { muted: this.muted, active: Boolean(this.context) && !this.muted }
  }

  notify() {
    const value = this.snapshot()
    this.listeners.forEach(listener => listener(value))
  }

  unlock() {
    if (this.muted || typeof window === 'undefined') return
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    if (!AudioContextClass) return

    if (!this.context) {
      this.context = new AudioContextClass()
      this.master = this.context.createGain()
      this.musicBus = this.context.createGain()
      this.sfxBus = this.context.createGain()
      this.master.gain.value = 0.72
      this.musicBus.gain.value = 1
      this.sfxBus.gain.value = 0.9
      this.musicBus.connect(this.master)
      this.sfxBus.connect(this.master)
      this.master.connect(this.context.destination)
      this.restartMusic()
    }

    if (this.context.state === 'suspended') void this.context.resume()
    this.notify()
  }

  setMuted(muted) {
    this.muted = muted
    try {
      window.localStorage.setItem(STORAGE_KEY, String(muted))
    } catch {
      // Audio still works when storage is unavailable.
    }

    if (!muted) this.unlock()
    if (this.context && this.master) {
      const now = this.context.currentTime
      this.master.gain.cancelScheduledValues(now)
      this.master.gain.setTargetAtTime(muted ? 0 : 0.72, now, 0.035)
    }
    this.notify()
  }

  setScene(scene) {
    if (!SCENES[scene] || scene === this.scene) return
    this.scene = scene
    this.step = 0
    if (this.context) this.restartMusic()
  }

  restartMusic() {
    if (this.timer) window.clearInterval(this.timer)
    const config = SCENES[this.scene]
    this.playMusicStep()
    this.timer = window.setInterval(() => this.playMusicStep(), config.interval)
  }

  playMusicStep() {
    if (!this.context || this.muted || this.context.state !== 'running') return
    const config = SCENES[this.scene]
    const index = this.step % config.notes.length
    this.tone({
      note: config.notes[index], duration: config.duration, level: config.level,
      type: config.wave, bus: this.musicBus, attack: 0.12,
    })
    if (index % 2 === 0) {
      this.tone({
        note: config.bass[Math.floor(index / 2) % config.bass.length],
        duration: config.duration * 1.45, level: config.level * 0.72,
        type: 'sine', bus: this.musicBus, attack: 0.18,
      })
    }
    this.step += 1
  }

  tone({ note, duration = 0.2, level = 0.08, type = 'sine', bus, attack = 0.01, delay = 0 }) {
    if (!this.context || this.muted) return
    const now = this.context.currentTime + delay
    const oscillator = this.context.createOscillator()
    const gain = this.context.createGain()
    const filter = this.context.createBiquadFilter()

    oscillator.type = type
    oscillator.frequency.setValueAtTime(midiToFrequency(note), now)
    filter.type = 'lowpass'
    filter.frequency.setValueAtTime(bus === this.musicBus ? 1450 : 2400, now)
    filter.Q.value = 0.7
    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(Math.max(level, 0.0002), now + attack)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + duration)

    oscillator.connect(filter)
    filter.connect(gain)
    gain.connect(bus ?? this.sfxBus)
    oscillator.start(now)
    oscillator.stop(now + duration + 0.04)
  }

  playCue(kind) {
    if (!this.context || this.muted || this.context.state !== 'running') return
    if (kind === 'click') {
      this.tone({ note: 76, duration: 0.06, level: 0.055, type: 'sine', bus: this.sfxBus })
      return
    }
    if (kind === 'danger') {
      ;[50, 45, 38].forEach((note, index) => this.tone({
        note, duration: 0.42, level: 0.11 - index * 0.018,
        type: 'sawtooth', bus: this.sfxBus, delay: index * 0.12,
      }))
      return
    }
    if (kind === 'positive') {
      ;[64, 67, 72].forEach((note, index) => this.tone({
        note, duration: 0.42, level: 0.085,
        type: 'triangle', bus: this.sfxBus, delay: index * 0.09,
      }))
      return
    }
    if (kind === 'complete') {
      ;[60, 64, 67, 72].forEach((note, index) => this.tone({
        note, duration: 0.85, level: 0.075,
        type: 'triangle', bus: this.sfxBus, delay: index * 0.12,
      }))
      return
    }
    ;[67, 72].forEach((note, index) => this.tone({
      note, duration: 0.2, level: 0.06,
      type: 'sine', bus: this.sfxBus, delay: index * 0.07,
    }))
  }

  suspendForVisibility(hidden) {
    if (!this.context) return
    if (hidden) void this.context.suspend()
    else if (!this.muted) void this.context.resume()
  }
}

export const gameAudio = new GameAudioEngine()
