'use strict'

const kErrors = Symbol('kErrors')

module.exports = function (errors) {
  errors = errors.filter(defined)

  if (errors.length === 0) return
  if (errors.length === 1) return errors[0]

  return new CombinedError(errors)
}

class CombinedError extends Error {
  constructor (errors) {
    const unique = new Set(errors.map(getMessage).filter(Boolean))
    const message = Array.from(unique).join('; ')

    super(message)

    value(this, 'name', 'CombinedError')
    value(this, kErrors, errors)

    getter(this, 'stack', () => errors.map(getStack).join('\n\n'))
    getter(this, 'transient', () => errors.length > 0 && errors.every(transient))
    getter(this, 'expected', () => errors.length > 0 && errors.every(expected))
  }

  [Symbol.iterator] () {
    return this[kErrors][Symbol.iterator]()
  }
}

function value (obj, prop, value) {
  Object.defineProperty(obj, prop, { value })
}

function getter (obj, prop, get) {
  Object.defineProperty(obj, prop, { get })
}

function defined (err) {
  return err != null
}

function getMessage (err) {
  return err.message
}

function getStack (err) {
  return err.stack
}

function transient (err) {
  return err.transient === true
}

function expected (err) {
  return err.expected === true
}
