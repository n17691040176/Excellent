import assert from 'node:assert/strict';
import test from 'node:test';

import { buildInviteUrl, extractInviteCode, resolveInviteWebBaseUrl } from './invite.js';

test('buildInviteUrl creates an H5 route with the invite code', () => {
  assert.equal(
    buildInviteUrl('https://example.com/', 'ABCD1234', undefined),
    'https://example.com/#/pages/login/index?invite_code=ABCD1234'
  );
});

test('buildInviteUrl resolves relative deployments against the current H5 origin', () => {
  const locationLike = {
    origin: 'https://mall.example.com',
    pathname: '/index.html'
  };

  assert.equal(resolveInviteWebBaseUrl('/', locationLike), 'https://mall.example.com');
  assert.equal(
    buildInviteUrl('/', 'ABCD1234', locationLike),
    'https://mall.example.com/#/pages/login/index?invite_code=ABCD1234'
  );
});

test('buildInviteUrl falls back to the current H5 location when config is empty', () => {
  assert.equal(
    buildInviteUrl('', 'ABCD1234', {
      origin: 'https://example.com',
      pathname: '/mobile/'
    }),
    'https://example.com/mobile/#/pages/login/index?invite_code=ABCD1234'
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
