// ARISE adapter: callers pass voiceHome explicitly; never touch Gentle settings.
export function gentlePiConfigHome() {
  throw new Error('ARISE requires an explicit voiceHome');
}
