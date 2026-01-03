"use client";

import { Clock } from "lucide-react";

interface DurationOption {
  value: "15" | "30" | "60";
  label: string;
  description: string;
  platform: string;
}

const durationOptions: DurationOption[] = [
  {
    value: "15",
    label: "15 seconds",
    description: "Quick, punchy content",
    platform: "TikTok, Reels",
  },
  {
    value: "30",
    label: "30 seconds",
    description: "Balanced coverage",
    platform: "Instagram, YouTube Shorts",
  },
  {
    value: "60",
    label: "60 seconds",
    description: "Full property showcase",
    platform: "All platforms",
  },
];

interface DurationSelectorProps {
  value: "15" | "30" | "60";
  onChange: (value: "15" | "30" | "60") => void;
}

export function DurationSelector({ value, onChange }: DurationSelectorProps) {
  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-gray-700">Video Duration</label>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {durationOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`relative flex flex-col items-center p-4 rounded-lg border-2 transition-all ${
              value === option.value
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300 bg-white"
            }`}
          >
            <Clock
              className={`h-8 w-8 mb-2 ${
                value === option.value ? "text-blue-500" : "text-gray-400"
              }`}
            />
            <span
              className={`text-lg font-semibold ${
                value === option.value ? "text-blue-700" : "text-gray-900"
              }`}
            >
              {option.label}
            </span>
            <span className="text-sm text-gray-500 mt-1">{option.description}</span>
            <span className="text-xs text-gray-400 mt-1">{option.platform}</span>
            {value === option.value && (
              <div className="absolute top-2 right-2 h-4 w-4 rounded-full bg-blue-500 flex items-center justify-center">
                <svg
                  className="h-3 w-3 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={3}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
