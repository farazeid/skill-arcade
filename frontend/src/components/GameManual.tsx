import React from "react";

const GameManual: React.FC = () => {
  return (
    <div>
      <h1 className="text-2xl md:text-3xl font-bold text-red-500">BREAKOUT</h1>
      <div className="text-left text-xs mt-4 text-gray-500">
        Controls: Left/Right Arrows (Move), Spacebar (Fire/Start)
      </div>
    </div>
  );
};

export default GameManual;
