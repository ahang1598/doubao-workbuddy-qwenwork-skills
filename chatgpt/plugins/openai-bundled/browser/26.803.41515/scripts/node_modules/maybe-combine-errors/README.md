# maybe-combine-errors

**Combine 0 or more errors into one.**

[![npm status](http://img.shields.io/npm/v/maybe-combine-errors.svg)](https://www.npmjs.org/package/maybe-combine-errors)
[![node](https://img.shields.io/node/v/maybe-combine-errors.svg)](https://www.npmjs.org/package/maybe-combine-errors)
[![Travis build status](https://img.shields.io/travis/com/vweevers/maybe-combine-errors.svg?label=travis)](http://travis-ci.com/vweevers/maybe-combine-errors)
[![JavaScript Style Guide](https://img.shields.io/badge/code_style-standard-brightgreen.svg)](https://standardjs.com)

## Usage

```js
const combine = require('maybe-combine-errors')

const err1 = new Error('one')
const err2 = new Error('two')

console.log(combine([err1, err2]).message)
console.log(combine([err1, err2]) instanceof Error)
console.log(combine([err1, null]) === err1)
console.log(combine([]) === undefined)

throw combine([err1, err2])
```

```
$ node example.js
one; two
true
true
true
example.js:9
throw combine([err1, err2])
^

Error: one
    at Object.<anonymous> (example.js:3:14)
    at Module._compile (internal/modules/cjs/loader.js:945:30)
    at Object.Module._extensions..js (internal/modules/cjs/loader.js:962:10)
    at Module.load (internal/modules/cjs/loader.js:798:32)
    at Function.Module._load (internal/modules/cjs/loader.js:711:12)
    at Function.Module.runMain (internal/modules/cjs/loader.js:1014:10)
    at internal/main/run_main_module.js:17:11

Error: two
    at Object.<anonymous> (example.js:4:14)
    at Module._compile (internal/modules/cjs/loader.js:945:30)
    at Object.Module._extensions..js (internal/modules/cjs/loader.js:962:10)
    at Module.load (internal/modules/cjs/loader.js:798:32)
    at Function.Module._load (internal/modules/cjs/loader.js:711:12)
    at Function.Module.runMain (internal/modules/cjs/loader.js:1014:10)
    at internal/main/run_main_module.js:17:11
```

## API

### `combine(errors)`

The `errors` argument must be an array.

Elements that are `null` or `undefined` are skipped. If the array is empty (after skipping `null` and `undefined`), `undefined` will be returned. If the array contains only 1 error, that error will be returned as-is. Otherwise, a combined error with joined messages and a lazily joined stack. Duplicate messages are skipped.

Respects [`transient-error`](https://github.com/vweevers/transient-error) and `err.expected`: if all errors have `.transient === true` then the combined error will also be transient. Same for `.expected`, which is useful for the following pattern:

```js
if (err.expected) {
  console.error(err.message)
  process.exit(1)
} else {
  throw err
}
```

## Alternatives

### [`combine-errors`](https://github.com/MatthewMueller/combine-errors)

Same message and stack behavior. Different in that it always returns an error regardless of input length.

### [`aggregate-error`](https://github.com/sindresorhus/aggregate-error)

Sets message to a joined stack, which means you can't get a human-friendly message with e.g. `console.error(err.message)`. Removes "mostly unhelpful" internal Node.js entries from the stack.

## Install

With [npm](https://npmjs.org) do:

```
npm install maybe-combine-errors
```

## License

[MIT](LICENSE.md) © 2020-present Vincent Weevers
