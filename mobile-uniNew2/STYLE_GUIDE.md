# Mobile UniNew2 Style Guide

## Purpose

This document summarizes the current visual language of `mobile-uniNew2` based on the existing pages and shared styles. It is intended to keep future page work visually consistent without changing the current product direction.

## Visual Direction

- Overall tone: warm commerce style
- Core keywords: cream background, orange-gold highlights, rounded cards, soft shadows, light glass effect, strong campaign feel
- Avoid: cold tech gradients, pure black text systems, flat admin-table style layouts, minimal monochrome interfaces

## Design Tokens

### Primary Palette

- Brand orange: `#ff6f00` to `#ff9f2f`
- Highlight orange: `#ff7a00`
- Warm gold-brown: `#bf8650`, `#c98d51`, `#d79e62`
- Base text dark: `#2b1b0f`, `#4a2b13`, `#503522`
- Secondary text: `#8c725d`, `#7d6753`, `#9b7450`
- Page background family: `#fff8f0`, `#fff4e8`, `#fffaf3`

### Functional Colors

- Positive / asset / income: green family such as `#1e8f64`, `#165b40`
- Service / neutral state: blue family such as `#225cc2`
- Promotion / CTA / price: orange family

### Background Treatment

- Do not use flat white as the page background
- Prefer soft radial + linear layered backgrounds
- Card backgrounds can use subtle white-to-cream gradients

## Layout Rules

- Use the shared `.container` spacing as the default page shell
- Default horizontal page padding: `24rpx`
- Default bottom breathing room: `36rpx`
- Section rhythm:
  - small spacing: `8rpx`, `12rpx`, `16rpx`
  - module spacing: `20rpx`, `24rpx`
- Pages are card-led, not divider-led

## Card System

- Standard card:
  - radius: about `24rpx`
  - padding: `24rpx`
  - soft border
  - warm shadow
- Compact card:
  - radius: about `18rpx`
  - padding: `18rpx`
- Cards should feel slightly elevated, not flat
- Keep subtle gradients or highlight spots on important cards

## Typography

- Main page title: `34-38rpx`, weight `700-800`
- Section title: around `32rpx`, weight `800`
- Body text: `22-24rpx`
- Caption / helper text: `20-23rpx`
- Price text is a separate hierarchy and should be visibly stronger than body text
- Avoid pure black text; continue using warm dark brown tones

## Buttons

- Primary button:
  - capsule shape
  - orange gradient
  - visible shadow
- Secondary button:
  - light orange background
  - orange text
- Avoid cold outline-only buttons unless there is a clear reason

## Badges and Status

- Continue using the shared badge system from `styles/common.css`
- Orange badge: promo, recommendation, emphasis
- Green badge: assets, income, positive status
- Blue badge: service, system state, local-life related content
- Badges should stay rounded and compact

## Motion and Interaction

- Keep motion light but noticeable
- Shared interactive feedback:
  - slight scale down on active state
  - slight opacity drop
- Custom tab bar is the strongest motion area in the app
- New pages should not exceed tab bar motion intensity

## Page Patterns

### Home

- Use a strong branded header
- Search, ticker, hero banner, quick entries, recommendation flow
- This page carries the most campaign/operation feel

### List Pages

- Use a head card plus segmented filters or tags
- Content should be card lists, not plain rows
- Product and service lists should keep cover area, title, desc, price, and action

### Profile / Center Pages

- Use a strong top hero card
- Support member, wallet, growth, asset, or operation entry blocks
- Grid entry sections should remain rounded and card-based

### Detail Pages

- Use a head card with summary info
- Then stack explanation / benefits / content cards
- Final CTA should be visually strong and obvious

## Shared Building Blocks

These are the current style anchors and should be reused instead of reinvented:

- `styles/common.css`
- `.card`
- `.card-tight`
- `.section-title`
- `.badge`
- `.btn-primary`
- `.btn-ghost`
- `.ecom-price`
- `.row-between`

## Custom Tab Bar

- Floating capsule layout
- Rounded full-pill background
- Active indicator
- Primary middle tab is visually lifted
- Supports glow and bounce feedback
- Treat it as a brand signature component

## Content Tone

- The interface style is premium-warm and commerce-oriented
- Copy should match that tone: direct, benefit-led, not technical
- Avoid backend/admin wording inside mobile pages

## Current Risks

- Many visible Chinese strings are still mojibake/garbled
- The style system itself is consistent, but text quality is reducing perceived polish
- If future work includes page cleanup, fixing text content should be treated as part of visual consistency

## Implementation Guidance

- Do not introduce a second visual system
- Extend current tokens before adding new colors
- Prefer modifying shared classes over one-off page overrides when the pattern is reusable
- If a page has a finance or asset theme, keep the same base language and only shift local accents toward green
- Preserve the current warm premium feel even when simplifying layouts
