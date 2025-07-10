export const manualDescription: string = `LEFT: ←
RIGHT: →
FIRE: Spacebar`;

export const relevantKeys: string[] = ["ArrowLeft", "ArrowRight", " "];

enum Action {
  NOOP = 0,
  FIRE = 1,
  RIGHT = 2,
  LEFT = 3,
}

export const determineAction = (keys: Set<string>): number => {
  const left = keys.has("ArrowLeft");
  const right = keys.has("ArrowRight");
  const fire = keys.has(" ");

  if (fire) return Action.FIRE;
  if (right) return Action.RIGHT;
  if (left) return Action.LEFT;

  return Action.NOOP;
};
