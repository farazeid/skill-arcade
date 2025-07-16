import React from "react";

type GameCanvasProps = {
  frame: string;
  isGameOver: boolean;
  isGameWon: boolean;
  onNewGame: () => void;
};

const GameCanvas: React.FC<GameCanvasProps> = ({
  frame,
  isGameOver,
  isGameWon,
  onNewGame,
}) => {
  return (
    <div id="gameContainer" className="relative w-full max-w-lg">
      <img id="gameImage" src={frame} alt="Game Screen" className="w-full" />
      {isGameOver && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex flex-col items-center justify-center">
          {isGameWon && (
            <h2 className="text-4xl font-bold text-white">WINNER</h2>
          )}
          {!isGameWon && (
            <h2 className="text-4xl font-bold text-white">GAME OVER</h2>
          )}
          <button
            onClick={onNewGame}
            className="mt-4 bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
          >
            New Game
          </button>
        </div>
      )}
    </div>
  );
};

export default GameCanvas;

// Streamed env observation
// Toggleable "WINNER"/"Game Over" overlay