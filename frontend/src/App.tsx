import { useState, useEffect, useRef } from "react";
import GameCanvas from "./components/GameCanvas";
import GameState from "./components/GameState";
import GameManual from "./components/GameManual";
import ServerStats from "./components/ServerStats";

function App() {
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(5);
  const [frame, setFrame] = useState(
    "https://placehold.co/160x210/000000/FFFFFF?text=Loading..."
  );
  const [isGameOver, setIsGameOver] = useState(false);
  const [status, setStatus] = useState("Connecting...");
  const [statusColor, setStatusColor] = useState("text-gray-500");
  const [clientFps, setClientFps] = useState(0);
  const [serverFps, setServerFps] = useState(0);

  const socket = useRef<WebSocket | null>(null);
  const pressedKeys = useRef(new Set<string>());
  const clientFrameCount = useRef(0);
  const lastFpsTime = useRef(performance.now());

  const keyMap: { [key: string]: string } = {
    ArrowLeft: "LEFT",
    ArrowRight: "RIGHT",
    " ": "FIRE", // Spacebar
  };

  useEffect(() => {
    function connectWebSocket() {
      // const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = import.meta.env.VITE_WS_URL;
      //  ||
      // `${wsProtocol}//${window.location.hostname}:8000/ws`;

      socket.current = new WebSocket(wsUrl);

      socket.current.onopen = () => {
        setStatus("Connected");
        setStatusColor("text-green-500");
      };

      socket.current.onmessage = (event: MessageEvent) => {
        clientFrameCount.current++;

        const state = JSON.parse(event.data);

        setScore(state.score);
        setLives(state.lives);
        setServerFps(state.serverFps || 0);
        setFrame(`data:image/jpeg;base64,${state.frame}`);

        if (state.gameOver) {
          setIsGameOver(true);
          setStatus("Game Over. Refresh to play again.");
          setStatusColor("text-red-500");

          if (socket.current) {
            socket.current.close();
          }
        }
      };

      socket.current.onclose = () => {
        if (!isGameOver) {
          setStatus("Disconnected. Refresh to play again.");
          setStatusColor("text-red-500");
        }
      };

      socket.current.onerror = (error: Event) => {
        console.error("WebSocket error:", error);
        setStatus("Connection Error.");
        setStatusColor("text-red-500");
      };
    }

    connectWebSocket();

    const sendAction = (action: string) => {
      if (socket.current && socket.current.readyState === WebSocket.OPEN) {
        socket.current.send(JSON.stringify({ type: "action", action: action }));
      }
    };

    const releaseAction = (action: string) => {
      if (socket.current && socket.current.readyState === WebSocket.OPEN) {
        socket.current.send(
          JSON.stringify({ type: "release_action", action: action })
        );
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      const action = keyMap[e.key];
      if (action && !pressedKeys.current.has(action)) {
        e.preventDefault();
        pressedKeys.current.add(action);
        sendAction(action);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const action = keyMap[e.key];
      if (action) {
        e.preventDefault();
        pressedKeys.current.delete(action);
        releaseAction(action);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    let animationFrameId: number;
    const updateFpsDisplay = () => {
      const now = performance.now();
      const delta = now - lastFpsTime.current;

      if (delta >= 1000) {
        // Update display once per second
        const fps = clientFrameCount.current / (delta / 1000);
        setClientFps(fps);
        clientFrameCount.current = 0;
        lastFpsTime.current = now;
      }
      animationFrameId = requestAnimationFrame(updateFpsDisplay);
    };

    updateFpsDisplay();

    return () => {
      if (socket.current) {
        socket.current.close();
      }
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      cancelAnimationFrame(animationFrameId);
    };
  }, [isGameOver]); // Re-run effect if isGameOver changes to handle onclose message properly

  return (
    <>
      <title>BRLL Skill Arcade</title>
      <div>
        Header: (1) Bath Reinforcement Learning Lab's Skill Arcade, (2) User
        Profile
      </div>
      <div className="flex items-center justify-center">
        <GameManual />
        <GameCanvas frame={frame} isGameOver={isGameOver} />

        <div>
          <GameState score={score} lives={lives} />
          <ServerStats
            status={status}
            statusColor={statusColor}
            clientFps={clientFps}
            serverFps={serverFps}
          />
        </div>
      </div>
      <div>
        Footer: (1) Feedback Form, (2) Contact Us, (3) Privacy Policy, (4) Terms
        of Service
      </div>
    </>
  );
}

export default App;
