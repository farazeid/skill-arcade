import { useEffect, useRef } from "react";

const keyMap: { [key: string]: string } = {
  ArrowUp: "UP",
  ArrowDown: "DOWN",
  ArrowLeft: "LEFT",
  ArrowRight: "RIGHT",
  " ": "FIRE", // Spacebar
};

const relevantKeys = Object.keys(keyMap);

const determineAction = (keys: Set<string>): string => {
  const up = keys.has("UP");
  const down = keys.has("DOWN");
  const left = keys.has("LEFT");
  const right = keys.has("RIGHT");
  const fire = keys.has("FIRE");

  if (up && right && fire) return "UPRIGHTFIRE";
  if (up && left && fire) return "UPLEFTFIRE";
  if (down && right && fire) return "DOWNRIGHTFIRE";
  if (down && left && fire) return "DOWNLEFTFIRE";

  if (up && fire) return "UPFIRE";
  if (right && fire) return "RIGHTFIRE";
  if (left && fire) return "LEFTFIRE";
  if (down && fire) return "DOWNFIRE";

  if (up && right) return "UPRIGHT";
  if (up && left) return "UPLEFT";
  if (down && right) return "DOWNRIGHT";
  if (down && left) return "DOWNLEFT";

  if (fire) return "FIRE";
  if (up) return "UP";
  if (right) return "RIGHT";
  if (left) return "LEFT";
  if (down) return "DOWN";

  return "NOOP";
};

export const useKeyboardInput = (
  socket: React.MutableRefObject<WebSocket | null>,
  isGameActive: boolean
) => {
  const pressedKeys = useRef(new Set<string>());
  const lastSentAction = useRef<string | null>(null);
  const actionTimer = useRef<number | null>(null);

  const sendAction = (action: string) => {
    if (
      socket.current &&
      socket.current.readyState === WebSocket.OPEN &&
      action !== lastSentAction.current
    ) {
      socket.current.send(JSON.stringify({ type: "action", action }));
      lastSentAction.current = action;
    }
  };

  const updateAndSend = () => {
    const action = determineAction(pressedKeys.current);
    sendAction(action);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isGameActive || !relevantKeys.includes(e.key)) return;
      e.preventDefault();
      pressedKeys.current.add(keyMap[e.key] || e.key);
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (!isGameActive || !relevantKeys.includes(e.key)) return;
      e.preventDefault();
      pressedKeys.current.delete(keyMap[e.key] || e.key);
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [isGameActive]);

  useEffect(() => {
    if (isGameActive) {
      lastSentAction.current = null;
      actionTimer.current = window.setInterval(updateAndSend, 1000 / 30); // 30 FPS
      updateAndSend(); // Initial action
    } else {
      if (actionTimer.current) {
        clearInterval(actionTimer.current);
        actionTimer.current = null;
      }
      pressedKeys.current.clear();
      if (socket.current?.readyState === WebSocket.OPEN) {
        sendAction("NOOP");
      }
    }
    return () => {
      if (actionTimer.current) {
        clearInterval(actionTimer.current);
        actionTimer.current = null;
      }
    };
  }, [isGameActive, socket]);
};
