import React from "react";

type GameStateProps = {
  score: number;
  lives: number;
};

const GameState: React.FC<GameStateProps> = ({ score, lives }) => {
  return (
    <div className="flex flex-col text-xl md:text-2xl">
      <div>SCORE: {score}</div>
      <div>LIVES: {lives}</div>
    </div>
  );
};

export default GameState;
