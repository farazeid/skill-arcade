type ControllerModule = {
  manualDescription: string;
  relevantKeys: string[];
  determineAction: (...args: any[]) => any;
  [key: string]: any;
};

export const loadController = async (
  gameId: string
): Promise<ControllerModule | null> => {
  try {
    const controllerModule = await import(`./${gameId}.ts`);
    return controllerModule;
  } catch (error) {
    console.error(`Failed to load controller for game: ${gameId}`, error);
    return null;
  }
};
