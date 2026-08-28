/**
 * Return the first enabled image swiper that is both configured in the page
 * layout and contains at least one usable image. Layout order is authoritative
 * when several swiper blocks are present; blocks omitted from layout fall back
 * to their custom_blocks order.
 */
export function selectImageSwiperBlock(payload) {
  const blocks = Array.isArray(payload?.custom_blocks) ? payload.custom_blocks : [];
  const layout = Array.isArray(payload?.layout) ? payload.layout : [];
  const layoutOrder = new Map(layout.map((key, index) => [String(key), index]));

  return blocks
    .map((block, index) => ({
      block,
      index,
      layoutIndex: layoutOrder.get(`custom:${block?.id}`) ?? Number.MAX_SAFE_INTEGER
    }))
    .filter(({ block }) => block?.enabled !== false && block?.type === 'image_swiper')
    .sort((left, right) => left.layoutIndex - right.layoutIndex || left.index - right.index)
    .map(({ block }) => block)
    .find((block) => (Array.isArray(block.items) ? block.items : [])
      .some((item) => item && item.enabled !== false && String(item.image_url || '').trim()));
}
