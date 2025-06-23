import { useState, useEffect, useRef } from "react";
import GameCanvas from "./components/GameCanvas";
import GameManual from "./components/GameManual";
import ServerStats from "./components/ServerStats";
import { useKeyboardInput } from "./hooks/useKeyboardInput";

function App() {
  const [frame, setFrame] = useState(
    "https://placehold.co/160x210/transparent/transparent?text="
  );
  const [isGameOver, setIsGameOver] = useState(false);
  const [status, setStatus] = useState("Select a game to start");
  const [statusColor, setStatusColor] = useState("text-gray-500");
  const [clientFps, setClientFps] = useState(0);
  const [serverFps, setServerFps] = useState(0);
  const [games, setGames] = useState<{ id: string; display_name: string }[]>(
    []
  );
  const [selectedGame, setSelectedGame] = useState<string | null>(null);
  const [gameDisplayName, setGameDisplayName] = useState("");
  const [gameActions, setGameActions] = useState<string[]>([]);

  const socket = useRef<WebSocket | null>(null);
  const clientFrameCount = useRef(0);
  const lastFpsTime = useRef(performance.now());

  useKeyboardInput(socket, !!selectedGame && !isGameOver);

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || "";
    fetch(`${apiUrl}/games`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setGames(data);
      })
      .catch((error) => {
        console.error("Fetching games failed:", error);
        setStatus("Failed to load games.");
        setStatusColor("text-red-500");
      });
  }, []);

  const handleGameSelected = (gameId: string) => {
    if (socket.current) {
      socket.current.close();
    }
    // Reset game state
    setFrame("https://placehold.co/160x210/000000/FFFFFF?text=Loading...");
    setIsGameOver(false);
    setStatus("Connecting...");
    setServerFps(0);
    setGameActions([]);

    setSelectedGame(gameId);
    const game = games.find((g) => g.id === gameId);
    if (game) {
      setGameDisplayName(game.display_name);
    }
  };

  useEffect(() => {
    if (!selectedGame) {
      return;
    }

    function connectWebSocket() {
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host =
        import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}`;
      const wsUrl = `${host}/ws/${selectedGame}`;

      socket.current = new WebSocket(wsUrl);

      socket.current.onopen = () => {
        setStatus("Connected");
        setStatusColor("text-green-500");
      };

      socket.current.onmessage = (event: MessageEvent) => {
        clientFrameCount.current++;
        const state = JSON.parse(event.data);

        // Update state from server message
        setServerFps(state.serverFps || 0);
        setFrame(`data:image/jpeg;base64,${state.frame}`);

        if (state.actions) {
          setGameActions(state.actions);
        }

        if (state.gameName && !gameDisplayName) {
          setGameDisplayName(state.gameName);
        }

        if (state.gameOver) {
          setIsGameOver(true);
          setStatus("Game Over. Select a game to play again.");
          setStatusColor("text-red-500");
          if (socket.current) {
            socket.current.close();
          }
        }
      };

      socket.current.onclose = () => {
        // Don't show disconnected message if we are in a game over state
        if (!isGameOver) {
          setStatus("Disconnected. Select a game to play again.");
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

    const animationFrameId = requestAnimationFrame(updateFpsDisplay);

    return () => {
      if (socket.current) {
        socket.current.close();
      }
      cancelAnimationFrame(animationFrameId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedGame]);

  // Moved out of useEffect to avoid re-creating it on every render
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
    requestAnimationFrame(updateFpsDisplay);
  };

  useEffect(() => {
    const animationFrameId = requestAnimationFrame(updateFpsDisplay);
    return () => cancelAnimationFrame(animationFrameId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <title>BRLL Skill Arcade</title>
      <div className="flex items-center justify-between w-full px-4">
        <div className="w-64">
          <GameManual
            games={games}
            onGameSelected={handleGameSelected}
            gameDisplayName={gameDisplayName}
            gameActions={gameActions}
          />
        </div>
        <GameCanvas frame={frame} isGameOver={isGameOver} />
        <div className="w-64">
          <ServerStats
            status={status}
            statusColor={statusColor}
            clientFps={clientFps}
            serverFps={serverFps}
          />
        </div>
      </div>
      <div className="text-center text-sm text-gray-500">
        Bath Reinforcement Learning Lab's Skill Arcade
      </div>
    </>
  );
}

export default App;
