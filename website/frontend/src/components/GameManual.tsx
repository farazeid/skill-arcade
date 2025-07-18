import React, { useState, useEffect, useRef } from "react";
import { loadController } from "../controllers/loader";

type GameManualProps = {
  games: { id: string; display_name: string }[];
  onGameSelected: (gameId: string) => void;
  gameDisplayName: string;
  gameId: string | null;
};

const GameManual: React.FC<GameManualProps> = ({
  games,
  onGameSelected,
  gameDisplayName,
  gameId,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [manualDescription, setManualDescription] = useState<string>("");

  useEffect(() => {
    if (gameId) {
      loadController(gameId).then((controller) => {
        if (controller) {
          setManualDescription(controller.manualDescription);
        }
      });
    } else {
      setManualDescription("Select a game to start.");
    }
  }, [gameId]);

  const handleOptionClick = (gameId: string) => {
    onGameSelected(gameId);
    setIsOpen(false);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [dropdownRef]);

  return (
    <div className="relative mx-auto text-center" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="text-2xl md:text-3xl font-bold text-green-500 hover:text-green-400 flex items-center focus:outline-none disabled:opacity-50"
        disabled={games.length === 0}
      >
        {gameDisplayName || "Select a Game"}
        <svg
          className="ml-2 -mr-1 h-12 w-12"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="origin-top-left absolute left-0 mt-2 w-max min-w-full rounded-xl shadow-lg bg-gray-700 ring-1 ring-black ring-opacity-5 focus:outline-none z-10 overflow-hidden">
          <div
            className="py-1"
            role="menu"
            aria-orientation="vertical"
            aria-labelledby="options-menu"
          >
            {games.length > 0 ? (
              games
                .sort((a, b) => a.display_name.localeCompare(b.display_name))
                .map((game) => (
                  <button
                    key={game.id}
                    onClick={() => handleOptionClick(game.id)}
                    className="block w-full text-left px-4 py-2 text-lg text-white hover:bg-gray-600"
                    role="menuitem"
                  >
                    {game.display_name}
                  </button>
                ))
            ) : (
              <div className="px-4 py-2 text-sm text-white">
                Loading games...
              </div>
            )}
          </div>
        </div>
      )}

      {gameId && (
        <div className="text-left text-xs mt-4 text-white">
          Controls:
          <br />
          <br />
          <span style={{ whiteSpace: "pre-line" }}>{manualDescription}</span>
        </div>
      )}
    </div>
  );
};

export default GameManual;
