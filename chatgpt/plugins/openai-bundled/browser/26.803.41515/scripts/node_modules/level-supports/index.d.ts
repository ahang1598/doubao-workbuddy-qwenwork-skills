/**
 * Given zero or more manifest objects, returns a merged and enriched manifest object
 * that has truthy properties for each of the features listed in {@link IManifest}.
 *
 * @param manifests Partial manifest(s) to merge.
 */
export function supports (...manifests: Array<Partial<IManifest>>): IManifest

/**
 * Describes the capabilities of an
 * [`abstract-level`](https://github.com/Level/abstract-level) database. Support matrices
 * for known `abstract-level` implementations can be found in
 * [`level-supports`](https://github.com/Level/supports#features).
 */
export interface IManifest {
  /**
   * Does the database read from a snapshot as described in
   * [`abstract-level`](https://github.com/Level/abstract-level#reading-from-snapshots)?
   */
  implicitSnapshots: boolean

  /**
   * Does the database implement `db.snapshot()` and do read methods accept a `snapshot`
   * option as described in
   * [`abstract-level`](https://github.com/Level/abstract-level#reading-from-snapshots)?
   */
  explicitSnapshots: boolean

  /**
   * Alias of {@link implicitSnapshots} for backwards compatibility.
   */
  snapshots: boolean

  /**
   * Does the database implement `has()` and `hasMany()`?
   */
  has: boolean

  /**
   * Does data survive after process (or environment) exit?
   */
  permanence: boolean

  /**
   * Do iterators support
   * [`seek(..)`](https://github.com/Level/abstract-level/#iteratorseektarget-options)?
   */
  seek: boolean

  /**
   * Does `db.open()` and the database constructor support this option?
   */
  createIfMissing: boolean

  /**
   * Does `db.open()` and the database constructor support this option?
   */
  errorIfExists: boolean

  /**
   * Can operations like `db.put()` be called without explicitly opening the db? Like so:
   *
   * ```js
   * const db = new Level()
   * await db.put('key', 'value')
   * ```
   *
   * Always true since `abstract-level@1`.
   */
  deferredOpen: boolean

  /**
   * Does database have the methods `createReadStream`, `createKeyStream` and
   * `createValueStream`, following the API documented in `levelup`? For `abstract-level`
   * databases, a standalone module called
   * [`level-read-stream`](https://github.com/Level/read-stream) is available.
   */
  streams: boolean

  /**
   * Which encodings (by name) does the database support, as indicated by nested
   * properties? For example:
   *
   * ```js
   * { utf8: true, json: true }
   * ```
   */
  encodings: Record<string, boolean>

  /**
   * Which events does the database emit, as indicated by nested properties? For example:
   *
   * ```js
   * if (db.supports.events.put) {
   *   db.on('put', listener)
   * }
   * ```
   */
  events: Record<string, boolean>

  /**
   * Declares support of additional methods, that are not part of the `abstract-level`
   * interface. In the form of:
   *
   * ```js
   * {
   *   foo: true,
   *   bar: true
   * }
   * ```
   *
   * Which says the db has two methods, `foo` and `bar`. It might be used like so:
   *
   * ```js
   * if (db.supports.additionalMethods.foo) {
   *   db.foo()
   * }
   * ```
   */
  additionalMethods: Record<string, boolean>

  /**
   * Which methods or method groups take a `signal` option? At the time of writing there
   * is only one method group: `iterators`. This includes `db.iterator()`, `db.keys()` and
   * `db.values()`. For example:
   *
   * ```js
   * if (db.supports.signals.iterators) {
   *   const ac = new AbortController()
   *   const iterator = db.keys({ signal: ac.signal })
   *
   *   ac.abort()
   * }
   * ```
   */
  signals: Record<string, boolean>
}
