import React from "react";

type ServerStatsProps = {
  status: string;
  statusColor: string;
  clientFps: number;
  serverFps: number;
  showFps?: boolean;
};

const ServerStats: React.FC<ServerStatsProps> = ({
  status,
  statusColor,
  clientFps,
  serverFps,
  showFps = false,
}) => {
  return (
    <div className="flex flex-col text-xs">
      <div id="status" className={`${statusColor}`}>
        {status}
      </div>
      {showFps && (
        <div id="fps" className="text-gray-500">
          <div>Client: {clientFps.toFixed(1)} FPS</div>
          <div>Server: {serverFps.toFixed(1)} FPS</div>
        </div>
      )}
    </div>
  );
};

export default ServerStats;
