export const manualDescription: string = `UP: ↑
DOWN: ↓
LEFT: ←
RIGHT: →
FIRE: Spacebar`;

export const relevantKeys: string[] = [
  "ArrowLeft",
  "ArrowRight",
  "ArrowUp",
  "ArrowDown",
  " ",
];

enum Action {
  NOOP = 0,
  FIRE = 1,
  UP = 2,
  RIGHT = 3,
  LEFT = 4,
  DOWN = 5,
  UPRIGHT = 6,
  UPLEFT = 7,
  DOWNRIGHT = 8,
  DOWNLEFT = 9,
  UPFIRE = 10,
  RIGHTFIRE = 11,
  LEFTFIRE = 12,
  DOWNFIRE = 13,
  UPRIGHTFIRE = 14,
  UPLEFTFIRE = 15,
  DOWNRIGHTFIRE = 16,
  DOWNLEFTFIRE = 17,
}

export const determineAction = (keys: Set<string>): number => {
  const up = keys.has("ArrowUp");
  const down = keys.has("ArrowDown");
  const left = keys.has("ArrowLeft");
  const right = keys.has("ArrowRight");
  const fire = keys.has(" ");

  if (up && right && fire) return Action.UPRIGHTFIRE;
  if (up && left && fire) return Action.UPLEFTFIRE;
  if (down && right && fire) return Action.DOWNRIGHTFIRE;
  if (down && left && fire) return Action.DOWNLEFTFIRE;

  if (up && fire) return Action.UPFIRE;
  if (right && fire) return Action.RIGHTFIRE;
  if (left && fire) return Action.LEFTFIRE;
  if (down && fire) return Action.DOWNFIRE;

  if (up && right) return Action.UPRIGHT;
  if (up && left) return Action.UPLEFT;
  if (down && right) return Action.DOWNRIGHT;
  if (down && left) return Action.DOWNLEFT;

  if (fire) return Action.FIRE;
  if (up) return Action.UP;
  if (right) return Action.RIGHT;
  if (left) return Action.LEFT;
  if (down) return Action.DOWN;

  return Action.NOOP;
};
