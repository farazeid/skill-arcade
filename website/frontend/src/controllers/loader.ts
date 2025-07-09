type ControllerModule = {
  manualDescription: string;
  relevantKeys: string[];
  determineAction: (...args: any[]) => any;
  [key: string]: any;
};

// Use import.meta.glob to make Vite aware of all possible controller modules
const modules = import.meta.glob<ControllerModule>("./*.ts");

export const loadController = async (
  gameId: string
): Promise<ControllerModule | null> => {
  const path = `./${gameId}.ts`;
  // Check if the requested controller exists in the modules found by Vite
  if (path in modules) {
    try {
      // Load the module
      const controllerModule = await modules[path]();
      return controllerModule;
    } catch (error) {
      console.error(`Failed to load controller for game: ${gameId}`, error);
      return null;
    }
  } else {
    console.error(`Controller for game not found: ${gameId}`);
    return null;
  }
};
