import assert from 'node:assert/strict';
import test from 'node:test';

import { buildInviteUrl, extractInviteCode } from './invite.js';

test('buildInviteUrl creates an H5 route with the invite code', () => {
  assert.equal(
    buildInviteUrl('https://example.com/', 'ABCD1234'),
    'https://example.com/#/pages/login/index?invite_code=ABCD1234'
  );
});

test('extractInviteCode accepts a raw code and invitation URLs', () => {
  assert.equal(extractInviteCode('ABCD1234'), 'ABCD1234');
  assert.equal(
    extractInviteCode('https://example.com/#/pages/login/index?invite_code=ABCD1234'),
    'ABCD1234'
  );
});

test('extractInviteCode rejects unrelated or oversized content', () => {
  assert.equal(extractInviteCode('https://example.com/products/12'), '');
  assert.equal(extractInviteCode('a'.repeat(33)), '');
});
