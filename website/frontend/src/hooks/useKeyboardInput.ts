import { useEffect, useRef, useState } from "react";
import { loadController } from "../controllers/loader";

type ContinuousActionController = {
  relevantKeys: string[];
  determineAction: (keys: Set<string>) => number;
};

type SequentialActionController = {
  relevantKeys: string[];
  determineAction: (from: string, to: string) => number | null;
};

type Controller = ContinuousActionController | SequentialActionController;

export const useKeyboardInput = (
  socket: React.MutableRefObject<WebSocket | null>,
  isGameActive: boolean,
  gameId: string | null
) => {
  const [controller, setController] = useState<Controller | null>(null);
  const pressedKeys = useRef(new Set<string>());
  const lastSentAction = useRef<number | null>(null);
  const actionTimer = useRef<number | null>(null);
  const fromKey = useRef<string | null>(null); // For sequential input

  useEffect(() => {
    let isMounted = true;
    if (gameId) {
      loadController(gameId).then((module) => {
        if (isMounted && module) {
          setController(module as unknown as Controller);
        }
      });
    } else {
      setController(null);
    }

    return () => {
      isMounted = false;
    };
  }, [gameId]);

  const sendAction = (action: number | null) => {
    if (
      action !== null &&
      socket.current &&
      socket.current.readyState === WebSocket.OPEN &&
      action !== lastSentAction.current
    ) {
      socket.current.send(JSON.stringify({ type: "action", action }));
      lastSentAction.current = action;
    }
  };

  const updateAndSendContinuousAction = () => {
    if (controller) {
      const action = (
        controller.determineAction as (keys: Set<string>) => number
      )(pressedKeys.current);
      sendAction(action);
    }
  };

  useEffect(() => {
    if (!isGameActive || !controller) return;

    const isSequential =
      controller.determineAction && controller.determineAction.length === 2;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!controller.relevantKeys || !controller.relevantKeys.includes(e.key))
        return;
      e.preventDefault();

      if (isSequential) {
        pressedKeys.current.add(e.key);
        if (!fromKey.current) {
          fromKey.current = e.key;
        }
      } else {
        pressedKeys.current.add(e.key);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (!controller.relevantKeys || !controller.relevantKeys.includes(e.key))
        return;
      e.preventDefault();

      if (isSequential) {
        pressedKeys.current.delete(e.key);
        if (e.key === fromKey.current) {
          // The key that was initially held down is released.
          // Reset fromKey.current only if no other keys are currently pressed.
          if (pressedKeys.current.size === 0) {
            fromKey.current = null;
          }
        } else {
          // This is the "to" key being released.
          if (fromKey.current && pressedKeys.current.has(fromKey.current)) {
            // Only send action if the "from" key is still held down.
            const action = (
              controller.determineAction as (
                from: string,
                to: string
              ) => number | null
            )(fromKey.current, e.key);
            sendAction(action);
          }
        }
      } else {
        pressedKeys.current.delete(e.key);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [isGameActive, controller]);

  useEffect(() => {
    if (isGameActive && controller) {
      const isSequential =
        controller.determineAction && controller.determineAction.length === 2;
      lastSentAction.current = null;
      fromKey.current = null;
      pressedKeys.current.clear();

      if (!isSequential) {
        actionTimer.current = window.setInterval(
          updateAndSendContinuousAction,
          1000 / 30
        ); // 30 FPS
        updateAndSendContinuousAction(); // Initial action
      }
    } else {
      if (actionTimer.current) {
        clearInterval(actionTimer.current);
        actionTimer.current = null;
      }
      pressedKeys.current.clear();
      fromKey.current = null;
      if (socket.current?.readyState === WebSocket.OPEN) {
        sendAction(null);
      }
    }
    return () => {
      if (actionTimer.current) {
        clearInterval(actionTimer.current);
        actionTimer.current = null;
      }
    };
  }, [isGameActive, socket, controller]);
};
