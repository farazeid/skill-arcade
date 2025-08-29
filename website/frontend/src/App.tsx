import { useState, useEffect, useRef } from "react";
import GameCanvas from "./components/GameCanvas.tsx";
import GameManual from "./components/GameManual.tsx";
import ServerStats from "./components/ServerStats.tsx";
import AuthModal from "./components/AuthModal.tsx";
import { useAuth } from "./context/AuthContext.tsx";
import { useKeyboardInput } from "./hooks/useKeyboardInput.ts";
import { loadController } from "./controllers/loader";

function App() {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const { currentUser, logout } = useAuth();

  const [frame, setFrame] = useState(
    "https://placehold.co/160x210/transparent/transparent?text="
  );
  const [isGameOver, setIsGameOver] = useState(false);
  const [isGameWon, setIsGameWon] = useState(false);
  const [status, setStatus] = useState("");
  const [statusColor, setStatusColor] = useState("text-gray-500");
  const [clientFps, setClientFps] = useState(0);
  const [serverFps, setServerFps] = useState(0);
  const [showFps, setShowFps] = useState(false);
  const [games, setGames] = useState<{ id: string; display_name: string }[]>(
    []
  );
  const [selectedGame, setSelectedGame] = useState<string | null>(null);
  const [gameDisplayName, setGameDisplayName] = useState<string>("");
  const [gameId, setGameId] = useState<string | null>(null);
  const [gameInstanceKey, setGameInstanceKey] = useState<number>(0);
  const [timeObsShown, setTimeObsShown] = useState<number>(
    performance.timeOrigin + performance.now()
  );
  const [showControls, setShowControls] = useState(false);
  const [controlsVisible, setControlsVisible] = useState(false);
  const [pendingGameId, setPendingGameId] = useState<string | null>(null);
  const [manualDescription, setManualDescription] = useState<string>("");

  const socket = useRef<WebSocket | null>(null);
  const clientFrameCount = useRef(0);
  const lastFpsTime = useRef(performance.now());

  useKeyboardInput(socket, !!selectedGame && !isGameOver, gameId, timeObsShown);

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

  useEffect(() => {
    (window as any).enableFpsCounter = () => setShowFps(true);
    (window as any).disableFpsCounter = () => setShowFps(false);
  }, []);

  const handleGameSelected = (gameId: string) => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }

    // Exit old game: close socket and reset state
    if (socket.current) {
      socket.current.close();
      socket.current = null;
    }
    setSelectedGame(null);
    setGameId(null);
    setGameDisplayName("");
    setIsGameOver(false);
    setIsGameWon(false);
    setFrame("https://placehold.co/160x210/transparent/transparent?text=");
    setStatusColor("text-gray-500");
    setServerFps(0);
    setClientFps(0);

    // Now show controls for the new game
    setPendingGameId(gameId);
    setShowControls(true);
    setControlsVisible(false);

    // Load manual description
    loadController(gameId).then((controller) => {
      if (controller) {
        setManualDescription(controller.manualDescription);
      } else {
        setManualDescription("No manual available.");
      }
    });
  };

  const handleStartGame = () => {
    setShowControls(false);
    setControlsVisible(true);
    if (pendingGameId) {
      // Now actually start the game
      setFrame("https://placehold.co/160x210/000000/FFFFFF?text=Loading...");
      setIsGameOver(false);
      setStatus("Connecting...");
      setServerFps(0);

      setSelectedGame(pendingGameId);
      const game = games.find((g) => g.id === pendingGameId);
      if (game) {
        setGameId(pendingGameId);
        setGameDisplayName(game.display_name);
      }
      setGameInstanceKey((prevKey) => prevKey + 1);
      setPendingGameId(null);
    }
  };

  useEffect(() => {
    if (!selectedGame || !currentUser) {
      return;
    }

    const connectWebSocket = async () => {
      const idToken = currentUser.token;
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host =
        import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}`;
      const fromPublicWebsite =
        window.location.hostname ===
        import.meta.env.VITE_PUBLIC_WEBSITE_HOSTNAME;
      const wsUrl = `${host}/ws/${selectedGame}?token=${idToken}&from_public_website=${fromPublicWebsite}`;

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

        requestAnimationFrame(() => {
          const timeObsShown = performance.timeOrigin + performance.now();
          setTimeObsShown(timeObsShown);
        });

        if (state.gameName && !gameDisplayName) {
          setGameDisplayName(state.gameName);
        }

        if (state.gameOver) {
          setIsGameOver(true);
          setIsGameWon(state.gameWon);
          if (socket.current) {
            socket.current.close();
          }
        }
      };

      socket.current.onclose = () => {
        setStatus("Disconnected. Select a game to play again.");
        setStatusColor("text-red-500");
      };

      socket.current.onerror = (error: Event) => {
        console.error("WebSocket error:", error);
        setStatus("Connection Error.");
        setStatusColor("text-red-500");
      };
    };

    connectWebSocket();

    const animationFrameId = requestAnimationFrame(updateFpsDisplay);

    return () => {
      if (socket.current) {
        socket.current.close();
      }
      cancelAnimationFrame(animationFrameId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedGame, currentUser, gameInstanceKey]);

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
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      <div className="relative min-h-screen">
        {/* Login Overlay */}
        {!currentUser && (
          <div className="absolute inset-0 bg-black bg-opacity-25 backdrop-blur-sm flex items-center justify-center z-30">
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="bg-green-500 hover:bg-green-400 text-white font-bold py-4 px-8 rounded-xl text-2xl shadow-lg"
            >
              Login to Play
            </button>
            <div className="absolute bottom-2 text-center text-sm 400 w-full">
              Bath Reinforcement Learning Lab's Skill Arcade
            </div>
          </div>
        )}

        {/* App content */}
        <div className="flex flex-col items-center justify-center min-h-screen">
          {currentUser && (
            <div className="absolute top-4 right-4 z-20">
              <div className="flex items-center space-x-4">
                <span className="italic 300">{currentUser.email}</span>
                <button
                  onClick={logout}
                  className="bg-red-500 hover:bg-red-400 text-white font-bold py-2 px-4 rounded-xl"
                >
                  Logout
                </button>
              </div>
            </div>
          )}

          {/* Centered Game Selector if no game is selected */}
          {!gameId ? (
            <div className="flex flex-col items-center justify-center flex-1">
              <GameManual
                games={games}
                onGameSelected={handleGameSelected}
                gameDisplayName={gameDisplayName}
                gameId={gameId}
                showControls={showControls}
                manualDescription={manualDescription}
                onStartGame={handleStartGame}
                controlsVisible={controlsVisible}
              />
            </div>
          ) : (
            // Main layout with sidebar once a game is selected
            <div className="flex flex-grow items-center justify-between w-full px-4">
              <div className="w-64">
                <GameManual
                  games={games}
                  onGameSelected={handleGameSelected}
                  gameDisplayName={gameDisplayName}
                  gameId={gameId}
                  showControls={showControls}
                  manualDescription={manualDescription}
                  onStartGame={handleStartGame}
                  controlsVisible={controlsVisible}
                />
              </div>
              <GameCanvas
                frame={frame}
                isGameOver={isGameOver}
                isGameWon={isGameWon}
                onNewGame={() => gameId && handleGameSelected(gameId)}
              />
              <div className="w-64">
                <ServerStats
                  status={status}
                  statusColor={statusColor}
                  clientFps={clientFps}
                  serverFps={serverFps}
                  showFps={showFps}
                />
              </div>
            </div>
          )}

          {currentUser && (
            <div className="text-center text-sm 500">
              Bath Reinforcement Learning Lab's Skill Arcade
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default App;
