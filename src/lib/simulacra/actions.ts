// Svelte actions the page uses.
import type { Action } from 'svelte/action';

/**
 * Moves the element to <body> while it's mounted. The time bar lives there,
 * beside the robot's frame and above it, so its frosted glass blurs the
 * robot the way it blurs the page.
 */
export const toBody: Action<HTMLElement> = (node) => {
  document.body.appendChild(node);
  return {
    destroy() {
      node.remove();
    },
  };
};
