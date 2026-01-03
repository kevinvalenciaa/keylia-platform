"use client";

import { Film, Zap, Star, Sparkles } from "lucide-react";

export type VideoModelType = "kling" | "kling_pro" | "kling_v2" | "veo3" | "veo3_fast" | "minimax" | "runway";

interface ModelOption {
  value: VideoModelType;
  label: string;
  description: string;
  quality: "standard" | "pro" | "premium";
  speed: "fast" | "medium" | "slow";
  recommended?: boolean;
}

const modelOptions: ModelOption[] = [
  {
    value: "kling",
    label: "Kling Standard",
    description: "Fast & reliable",
    quality: "standard",
    speed: "fast",
  },
  {
    value: "kling_v2",
    label: "Kling V2 Pro",
    description: "Cinematic visuals",
    quality: "premium",
    speed: "medium",
    recommended: true,
  },
  {
    value: "veo3",
    label: "Veo 3.1",
    description: "Most realistic",
    quality: "premium",
    speed: "slow",
  },
  {
    value: "minimax",
    label: "MiniMax",
    description: "Film-like colors",
    quality: "pro",
    speed: "medium",
  },
  {
    value: "runway",
    label: "Runway Gen3",
    description: "Professional grade",
    quality: "pro",
    speed: "medium",
  },
  {
    value: "veo3_fast",
    label: "Veo 3.1 Fast",
    description: "Realistic & quick",
    quality: "pro",
    speed: "fast",
  },
];

interface ModelSelectorProps {
  value: VideoModelType;
  onChange: (value: VideoModelType) => void;
}

export function ModelSelector({ value, onChange }: ModelSelectorProps) {
  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
        <Film className="h-4 w-4 text-purple-500" />
        Video Quality Model
      </label>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {modelOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`relative flex flex-col items-start p-3 rounded-lg border-2 transition-all text-left ${
              value === option.value
                ? "border-purple-500 bg-purple-50"
                : "border-gray-200 hover:border-gray-300 bg-white"
            }`}
          >
            {option.recommended && (
              <span className="absolute -top-2 -right-2 px-2 py-0.5 bg-purple-500 text-white text-xs rounded-full flex items-center gap-1">
                <Star className="h-3 w-3" />
                Best
              </span>
            )}
            <span
              className={`font-medium text-sm ${
                value === option.value ? "text-purple-700" : "text-gray-900"
              }`}
            >
              {option.label}
            </span>
            <span className="text-xs text-gray-500 mt-0.5">
              {option.description}
            </span>
            <div className="flex gap-2 mt-2">
              <span
                className={`text-xs px-1.5 py-0.5 rounded ${
                  option.quality === "premium"
                    ? "bg-yellow-100 text-yellow-700"
                    : option.quality === "pro"
                    ? "bg-blue-100 text-blue-700"
                    : "bg-gray-100 text-gray-600"
                }`}
              >
                {option.quality === "premium" ? "Premium" : option.quality === "pro" ? "Pro" : "Standard"}
              </span>
              <span
                className={`text-xs px-1.5 py-0.5 rounded flex items-center gap-1 ${
                  option.speed === "fast"
                    ? "bg-green-100 text-green-700"
                    : option.speed === "medium"
                    ? "bg-orange-100 text-orange-700"
                    : "bg-red-100 text-red-700"
                }`}
              >
                <Zap className="h-3 w-3" />
                {option.speed}
              </span>
            </div>
          </button>
        ))}
      </div>
      <p className="text-xs text-gray-500">
        Premium models produce more cinematic, studio-quality results but take longer to generate.
      </p>
    </div>
  );
}
