import assert from 'node:assert/strict';
import test from 'node:test';

import { selectImageSwiperBlock } from './home-decoration.js';

test('selects the first swiper with an image in layout order', () => {
  const blockWithoutImage = { id: 'primary', type: 'image_swiper', items: [{ image_url: '' }] };
  const configuredBlock = { id: 'campaign', type: 'image_swiper', items: [{ image_url: '/uploads/campaign.png' }] };

  assert.equal(
    selectImageSwiperBlock({
      custom_blocks: [blockWithoutImage, configuredBlock],
      layout: ['custom:primary', 'custom:campaign']
    }),
    configuredBlock
  );
});

test('keeps the earlier configured swiper when both contain images', () => {
  const first = { id: 'first', type: 'image_swiper', items: [{ image_url: '/uploads/first.png' }] };
  const second = { id: 'second', type: 'image_swiper', items: [{ image_url: '/uploads/second.png' }] };

  assert.equal(
    selectImageSwiperBlock({
      custom_blocks: [second, first],
      layout: ['custom:first', 'custom:second']
    }),
    first
  );
});

test('ignores disabled blocks and items', () => {
  assert.equal(
    selectImageSwiperBlock({
      custom_blocks: [
        { id: 'disabled', type: 'image_swiper', enabled: false, items: [{ image_url: '/uploads/disabled.png' }] },
        { id: 'empty', type: 'image_swiper', items: [{ enabled: false, image_url: '/uploads/hidden.png' }] }
      ]
    }),
    undefined
  );
});
