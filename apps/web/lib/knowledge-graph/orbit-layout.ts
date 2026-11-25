type OrbitCard = { id: string; cardWidth?: number };

/** Lay out ranked groups on as many concentric rings as their cards require. */
export function buildOrbitLayout(groups: OrbitCard[][], width: number, height: number) {
  const positions = new Map<string, { x: number; y: number }>();
  const radii: number[] = [];
  const outerGuide = Math.max(150, Math.min(width, height) * .43);
  const guides = [Math.min(52, outerGuide * .12), outerGuide * .4, outerGuide * .7, outerGuide];
  // The diagonal bounds each horizontal card regardless of its angular position on a ring.
  const maxCardWidth = Math.max(104, ...groups.flat().map((card) => card.cardWidth ?? 120));
  const spacing = Math.hypot(maxCardWidth, 44) + 12;
  let outerOccupiedRadius = -Infinity;

  groups.forEach((group, rank) => {
    if (group.length === 0) {
      const guide = guides[rank];
      if (!radii.includes(guide)) radii.push(guide);
      return;
    }
    let radius = Math.max(guides[rank], outerOccupiedRadius + spacing);
    let offset = 0;
    while (offset < group.length) {
      // Neighbors on the same ring must have a chord at least one card diagonal long.
      const capacity = radius < spacing / 2
        ? 1
        : Math.floor(Math.PI / Math.asin(spacing / (2 * radius)));
      const count = Math.min(capacity, group.length - offset);
      radii.push(radius);
      group.slice(offset, offset + count).forEach((card, index) => {
        const angle = -Math.PI / 2 + index / count * Math.PI * 2;
        positions.set(card.id, {
          x: width / 2 + Math.cos(angle) * radius,
          y: height / 2 + Math.sin(angle) * radius,
        });
      });
      offset += count;
      outerOccupiedRadius = radius;
      radius += spacing;
    }
  });
  return { positions, radii: radii.sort((a, b) => a - b) };
}
