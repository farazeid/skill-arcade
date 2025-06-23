import React from "react";

type GameCanvasProps = {
  frame: string;
  isGameOver: boolean;
};

const GameCanvas: React.FC<GameCanvasProps> = ({ frame, isGameOver }) => {
  return (
    <div id="gameContainer" className="relative w-full max-w-lg">
      <img id="gameImage" src={frame} alt="Game Screen" className="w-full" />
      {isGameOver && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex flex-col items-center justify-center">
          <h2 className="text-4xl font-bold text-white">GAME OVER</h2>
          <div className="text-white">Refresh the page to restart</div>
        </div>
      )}
    </div>
  );
};

export default GameCanvas;

// Streamed env observation
// Toggleable "Game Over" overlay
