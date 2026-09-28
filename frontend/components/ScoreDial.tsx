import React from "react";

interface Props {
  score: number;
  size?: number;
  label?: string;
  animate?: boolean;
}

export function ScoreDial({ score, size = 120, label = "YuktiFi Score", animate = true }: Props) {
  const strokeWidth = size * 0.08;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  let color = "text-warm-secondary";
  if (score < 50) color = "text-red-600";
  else if (score < 75) color = "text-orange-500";

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="w-full h-full transform -rotate-90" viewBox={`0 0 ${size} ${size}`}>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-warm-border"
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="square"
            className={`${color} ${animate ? "transition-all duration-1000 ease-out" : ""}`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className={`text-3xl font-sans font-bold ${color}`}>{Math.round(score)}</span>
        </div>
      </div>
      {label && <span className="mt-2 text-[10px] font-sans text-warm-muted tracking-widest uppercase">{label}</span>}
    </div>
  );
}

