"use client";

import { Sparkles } from "lucide-react";

interface StyleOption {
  value: string;
  label: string;
  description: string;
}

const toneOptions: StyleOption[] = [
  { value: "luxury", label: "Luxury", description: "Elegant and sophisticated" },
  { value: "modern", label: "Modern", description: "Clean and contemporary" },
  { value: "cozy", label: "Cozy", description: "Warm and inviting" },
  { value: "minimal", label: "Minimal", description: "Simple and serene" },
  { value: "bold", label: "Bold", description: "Dynamic and striking" },
];

const paceOptions: StyleOption[] = [
  { value: "slow", label: "Slow", description: "Relaxed pace" },
  { value: "moderate", label: "Moderate", description: "Balanced pace" },
  { value: "fast", label: "Fast", description: "Energetic pace" },
];

type ToneType = "luxury" | "cozy" | "modern" | "minimal" | "bold";
type PaceType = "slow" | "moderate" | "fast";

interface StyleSelectorProps {
  tone: ToneType;
  pace: PaceType;
  onToneChange: (value: ToneType) => void;
  onPaceChange: (value: PaceType) => void;
}

export function StyleSelector({
  tone,
  pace,
  onToneChange,
  onPaceChange,
}: StyleSelectorProps) {
  return (
    <div className="space-y-6">
      {/* Tone Selection */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-blue-500" />
          Video Style
        </label>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {toneOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onToneChange(option.value as ToneType)}
              className={`flex flex-col items-center p-3 rounded-lg border-2 transition-all ${
                tone === option.value
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300 bg-white"
              }`}
            >
              <span
                className={`font-medium text-sm ${
                  tone === option.value ? "text-blue-700" : "text-gray-900"
                }`}
              >
                {option.label}
              </span>
              <span className="text-xs text-gray-500 mt-0.5">
                {option.description}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Pace Selection */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-700">Pacing</label>
        <div className="flex gap-2">
          {paceOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onPaceChange(option.value as PaceType)}
              className={`flex-1 py-2 px-4 rounded-lg border-2 transition-all ${
                pace === option.value
                  ? "border-blue-500 bg-blue-50 text-blue-700"
                  : "border-gray-200 hover:border-gray-300 bg-white text-gray-700"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
