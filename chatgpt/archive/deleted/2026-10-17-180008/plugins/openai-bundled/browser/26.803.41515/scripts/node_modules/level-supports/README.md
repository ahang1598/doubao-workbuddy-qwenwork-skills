# level-supports

**Create a manifest describing the abilities of an [`abstract-level`](https://github.com/Level/abstract-level) database.** No longer compatible with [`levelup`](https://github.com/Level/levelup) or [`abstract-leveldown`](https://github.com/Level/abstract-leveldown) since version 3.0.0.

[![level badge][level-badge]](https://github.com/Level/awesome)
[![npm](https://img.shields.io/npm/v/level-supports.svg)](https://www.npmjs.com/package/level-supports)
[![Node version](https://img.shields.io/node/v/level-supports.svg)](https://www.npmjs.com/package/level-supports)
[![Test](https://img.shields.io/github/actions/workflow/status/Level/supports/test.yml?branch=main\&label=test)](https://github.com/Level/level/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/codecov/c/github/Level/supports?label=\&logo=codecov\&logoColor=fff)](https://codecov.io/gh/Level/supports)
[![Standard](https://img.shields.io/badge/standard-informational?logo=javascript\&logoColor=fff)](https://standardjs.com)
[![Common Changelog](https://common-changelog.org/badge.svg)](https://common-changelog.org)
[![Donate](https://img.shields.io/badge/donate-orange?logo=open-collective\&logoColor=fff)](https://opencollective.com/level)

## Usage

```js
const { supports } = require('level-supports')

db.supports = supports({
  permanence: false,
  encodings: {
    utf8: true
  }
})
```

Receivers of the db can then use it like so:

```js
if (!db.supports.permanence) {
  throw new Error('Persistent storage is required')
}
```

## API

### `manifest = supports([manifest, ..])`

Given zero or more manifest objects, returns a merged and enriched manifest object that has truthy properties for each of the features listed below.

For future extensibility, the properties are truthy rather than strictly typed booleans. Falsy or absent properties are converted to `false`, other values are allowed:

```js
supports().seek // false
supports({ seek: true }).seek // true
supports({ seek: {} }).seek // {}
supports({ seek: 1 }, { seek: 2 }).seek // 2
```

For consumers of the manifest this means they should check support like so:

```js
if (db.supports.seek)
```

Rather than:

```js
if (db.supports.seek === true)
```

**Note:** the manifest describes high-level features that typically encompass multiple methods of a db. It is currently not a goal to describe a full API, or versions of it.

## Features

### `implicitSnapshots` (boolean)

Does the database read from a snapshot as described in [`abstract-level`](https://github.com/Level/abstract-level#reading-from-snapshots)? Must be `false` if any of the following is true:

- Reads don't operate on a snapshot
- Snapshots are created asynchronously.

Aliased as `snapshots` for backwards compatibility.

<details>
<summary>Support matrix</summary>

| Module          | Implicit snapshots          |
| :-------------- | :-------------------------- |
| `classic-level` | ✅                           |
| `memory-level`  | ✅                           |
| `browser-level` | ❌                           |
| `level`         | ✅                           |
| `many-level`    | ✅ (unless `retry` is true)  |
| `rave-level`    | ❌ (unless `retry` is false) |

</details>

### `explicitSnapshots` (boolean)

Does the database implement `db.snapshot()` and do read methods accept a `snapshot` option as described in [`abstract-level`](https://github.com/Level/abstract-level#reading-from-snapshots)?

<details>
<summary>Support matrix</summary>

| Module          | Explicit snapshots |
| :-------------- | :----------------- |
| `classic-level` | Not yet            |
| `memory-level`  | Not yet            |
| `browser-level` | ❌                  |
| `many-level`    | TBD                |
| `rave-level`    | TBD                |

</details>

### `has` (boolean)

Does the database implement `has()` and `hasMany()`? Tracked in [Level/community#142](https://github.com/Level/community/issues/142).

<details>
<summary>Support matrix</summary>

| Module          | Has     |
| :-------------- | :------ |
| `classic-level` | Not yet |
| `memory-level`  | Not yet |
| `browser-level` | Not yet |
| `many-level`    | Not yet |
| `rave-level`    | Not yet |

</details>

### `permanence` (boolean)

Does data survive after process (or environment) exit? Typically true. False for [`memory-level`](https://github.com/Level/memory-level).

### `seek` (boolean)

Do iterators support [`seek(..)`](https://github.com/Level/abstract-level/#iteratorseektarget-options)?

<details>
<summary>Support matrix</summary>

| Module           | Support |
| :--------------- | :------ |
| `abstract-level` | ✅ 1.0.0 |
| `classic-level`  | ✅ 1.0.0 |
| `memory-level`   | ✅ 1.0.0 |
| `browser-level`  | ✅ 1.0.0 |
| `level`          | ✅ 8.0.0 |
| `many-level`     | ✅ 1.0.0 |
| `rave-level`     | ✅ 1.0.0 |

</details>

### `deferredOpen` (boolean)

Can operations like `db.put()` be called without explicitly opening the db? Like so:

```js
const db = new Level()
await db.put('key', 'value')
```

Always true since `abstract-level@1`.

### `createIfMissing`, `errorIfExists` (boolean)

Does `db.open()` support these options?

<details>
<summary>Support matrix</summary>

| Module          | Support |
| :-------------- | :------ |
| `classic-level` | ✅       |
| `memory-level`  | ❌       |
| `browser-level` | ❌       |

</details>

### `events` (object)

Which events does the database emit, as indicated by nested properties? For example:

```js
if (db.supports.events.put) {
  db.on('put', listener)
}
```

### `streams` (boolean)

Does database have the methods `createReadStream`, `createKeyStream` and `createValueStream`, following the API documented in the legacy `levelup` module? Always false since the introduction of `abstract-level` which moved streams to a standalone module called [`level-read-stream`](https://github.com/Level/read-stream).

### `encodings` (object)

Which encodings (by name) does the database support, as indicated by nested properties? For example:

```js
{ utf8: true, json: true }
```

As the `encodings` property cannot be false (anymore, since `level-supports` v3.0.0) it implies that the database supports `keyEncoding` and `valueEncoding` options on all relevant methods, uses a default encoding of utf8 and that hence all of its read operations return strings rather than buffers by default.

<details>
<summary>Support matrix (specific encodings)</summary>

_This matrix lists which encodings are supported as indicated by e.g. `db.supports.encodings.utf8`. Encodings that encode to another (like how `'json'` encodes to `'utf8'`) are excluded here, though they are present in `db.supports.encodings`._

| Module          | `'utf8'`      | `'buffer'`    | `'view'`      |
| :-------------- | :------------ | :------------ | :------------ |
| `classic-level` | ✅             | ✅             | ✅ <sup>1<sup> |
| `memory-level`  | ✅ <sup>2<sup> | ✅ <sup>2<sup> | ✅ <sup>2<sup> |
| `browser-level` | ✅ <sup>1<sup> | ✅ <sup>1<sup> | ✅             |
| `level@8`       | ✅ <sup>3<sup> | ✅ <sup>3<sup> | ✅ <sup>3<sup> |

<small>

1. Transcoded (which may have a performance impact).
2. Can be controlled via `storeEncoding` option.
3. Whether it's transcoded depends on environment (Node.js or browser).

</small>

</details>

### `additionalMethods` (object)

Declares support of additional methods, that are not part of the `abstract-level` interface. In the form of:

```js
{
  foo: true,
  bar: true
}
```

Which says the db has two methods, `foo` and `bar`. It might be used like so:

```js
if (db.supports.additionalMethods.foo) {
  db.foo()
}
```

For future extensibility, the properties of `additionalMethods` should be taken as truthy rather than strictly typed booleans. We may add additional metadata (see [#1](https://github.com/Level/supports/issues/1)).

### `signals` (object)

Which methods or method groups take a `signal` option? At the time of writing there is only one method group: `iterators`. This includes `db.iterator()`, `db.keys()` and `db.values()`. For example:

```js
if (db.supports.signals.iterators) {
  const ac = new AbortController()
  const iterator = db.keys({ signal: ac.signal })

  ac.abort()
}
```

## Install

With [npm](https://npmjs.org) do:

```
npm install level-supports
```

## Contributing

[`Level/supports`](https://github.com/Level/supports) is an **OPEN Open Source Project**. This means that:

> Individuals making significant and valuable contributions are given commit-access to the project to contribute as they see fit. This project is more like an open wiki than a standard guarded open source project.

See the [Contribution Guide](https://github.com/Level/community/blob/master/CONTRIBUTING.md) for more details.

## Donate

Support us with a monthly donation on [Open Collective](https://opencollective.com/level) and help us continue our work.

## License

[MIT](LICENSE)

[level-badge]: https://leveljs.org/img/badge.svg
