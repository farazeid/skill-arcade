export const manualDescription: string = `Keys 1, 2, 3 refer to the left, middle, and 
right poles respectively.

To move a block between poles:
  1. Hold down the key for the pole the block is from
  2. Then press+release the key for the pole the block goes to`;

export const relevantKeys: string[] = ["1", "2", "3"];

enum Action {
  One2Two = 0,
  One2Three = 1,
  Two2One = 2,
  Two2Three = 3,
  Three2One = 4,
  Three2Two = 5,
}

export const determineAction = (from: string, to: string): number | null => {
  const actionMap: { [key: string]: number } = {
    "12": 0,
    "13": 1,
    "21": 2,
    "23": 3,
    "31": 4,
    "32": 5,
  };

  const key = `${from}${to}`;
  if (key in actionMap) {
    const action = actionMap[key];
    return action;
  } else {
    console.error(`Invalid Hanoi action: from ${from} to ${to}`);
    return null;
  }
};
