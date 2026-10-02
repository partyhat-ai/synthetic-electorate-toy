// Svelte actions the page uses.
import type { Action } from 'svelte/action';

/**
 * Moves the element to <body> while it's mounted. The time bar lives there,
 * beside the robot's frame and above it, so its frosted glass blurs the
 * robot the way it blurs the page; an open InfoPopover too, above both.
 */
export const toBody: Action<HTMLElement> = (node) => {
  document.body.appendChild(node);
  return {
    destroy() {
      node.remove();
    },
  };
};

/**
 * Reports the tallest the element has been since the window last changed
 * width (each change starts over), as it resizes.
 */
export const tallest: Action<HTMLElement, (px: number) => void> = (node, report) => {
  let onHeight = report;
  let width = innerWidth;
  let most = 0;
  const ro = new ResizeObserver(() => {
    if (innerWidth !== width) {
      width = innerWidth;
      most = 0;
    }
    const h = node.offsetHeight;
    if (h <= most) return;
    most = h;
    onHeight(most);
  });
  ro.observe(node);
  return {
    update(next) {
      onHeight = next;
    },
    destroy() {
      ro.disconnect();
    },
  };
};
