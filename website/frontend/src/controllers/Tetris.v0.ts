export const manualDescription: string = `LEFT: ←
RIGHT: →
DOWN: ↓
ROTATE CLOCKWISE: ↑
SWAP: S
DROP: Spacebar`;

export const relevantKeys: string[] = [
  "ArrowLeft",
  "ArrowRight",
  "ArrowDown",
  "ArrowUp",
  "s",
  " ",
];

enum Action { // Altered from: https://max-we.github.io/Tetris-Gymnasium/utilities/mappings/
  LEFT = 0,
  RIGHT = 1,
  DOWN = 2,
  ROTATE_CLOCKWISE = 3,
  // ROTATE_COUNTERCLOCKWISE = 4,
  HARD_DROP = 5,
  SWAP = 6,
  NOOP = 7,
}

export const determineAction = (keys: Set<string>): number => {
  const left = keys.has("ArrowLeft");
  const right = keys.has("ArrowRight");
  const down = keys.has("ArrowDown");
  const up = keys.has("ArrowUp");
  const swap = keys.has("s");
  const drop = keys.has(" ");

  // Prioritise
  if (up) return Action.ROTATE_CLOCKWISE;
  // if (rotateCounterClockwise) return Action.ROTATE_COUNTERCLOCKWISE;
  if (swap) return Action.SWAP;
  if (drop) return Action.HARD_DROP;

  if (left) return Action.LEFT;
  if (right) return Action.RIGHT;
  if (down) return Action.DOWN;

  return Action.NOOP;
};
