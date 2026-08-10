'use strict'

exports.supports = function supports (...manifests) {
  const manifest = manifests.reduce((acc, m) => Object.assign(acc, m), {})

  // Snapshots is an alias for backwards compatibility
  const implicitSnapshots = manifest.implicitSnapshots || manifest.snapshots || false
  const explicitSnapshots = manifest.explicitSnapshots || false

  return Object.assign(manifest, {
    implicitSnapshots,
    explicitSnapshots,
    snapshots: implicitSnapshots,
    has: manifest.has || false,
    permanence: manifest.permanence || false,
    seek: manifest.seek || false,
    createIfMissing: manifest.createIfMissing || false,
    errorIfExists: manifest.errorIfExists || false,
    deferredOpen: manifest.deferredOpen || false,
    streams: manifest.streams || false,
    encodings: Object.assign({}, manifest.encodings),
    events: Object.assign({}, manifest.events),
    additionalMethods: Object.assign({}, manifest.additionalMethods),
    signals: Object.assign({}, manifest.signals)
  })
}
