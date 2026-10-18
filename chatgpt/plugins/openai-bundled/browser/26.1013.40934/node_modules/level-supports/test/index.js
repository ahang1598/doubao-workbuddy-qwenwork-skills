'use strict'

const shape = require('./shape')
const cloneable = require('./cloneable')

module.exports = function suite (test, testCommon) {
  test('db has manifest', async function (t) {
    const db = testCommon.factory()
    const manifest = db.supports

    shape(t, manifest)
    cloneable(t, manifest)

    const before = Object.assign({}, manifest, {
      additionalMethods: Object.assign({}, manifest.additionalMethods)
    })

    await db.open()
    t.same(db.supports, before, 'manifest did not change after open')

    await db.close()
    t.same(db.supports, before, 'manifest did not change after close')
  })
}
