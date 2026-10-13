import test from 'node:test';
import assert from 'node:assert/strict';
import { draggedBounds, exceedsDragThreshold, snapBounds } from '../../src/main/drag';

test('drag begins only at the four-pixel movement threshold', () => {
  assert.equal(exceedsDragThreshold({ x: 10, y: 10 }, { x: 13, y: 10 }), false);
  assert.equal(exceedsDragThreshold({ x: 10, y: 10 }, { x: 14, y: 10 }), true);
  assert.equal(exceedsDragThreshold({ x: 0, y: 0 }, { x: 3, y: 3 }), true);
});

test('dragged bounds preserve size and apply rounded cursor delta', () => {
  assert.deepEqual(
    draggedBounds({ x: 100, y: 200, width: 256, height: 256 }, { x: 10, y: 10 }, { x: 27.6, y: 4.4 }),
    { x: 118, y: 194, width: 256, height: 256 },
  );
});

test('snap bounds attach near work-area edges', () => {
  assert.deepEqual(
    snapBounds({ x: 12, y: 742, width: 256, height: 256 }, { x: 0, y: 0, width: 1440, height: 1000 }),
    { x: 0, y: 744, width: 256, height: 256 },
  );
});
