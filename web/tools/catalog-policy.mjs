// Legacy one-bit speech/music fixtures stay downloadable for historical links,
// but are no longer offered in the public player library. Use provenance,
// not a codec-name substring: an IMA file can target a different sound device.
const uncataloguedPdmAliases = new Set([
  'ZX-audiobook-IMA4-flutter-check.trd',
  'ZX-music-Sea-Foam-IMA4-direct.trd',
  'ZX-music-Sea-Foam-RAM-auto.trd',
]);

export function showInLibrary(path, entry, group) {
  return !(path.startsWith('audiobook-beeper/')
    || entry?.group?.startsWith('audiobook-beeper/')
    || group?.guide?.startsWith('audiobook-beeper/')
    || group?.scripts?.some(script => script.startsWith('audiobook-beeper/'))
    || uncataloguedPdmAliases.has(path));
}
