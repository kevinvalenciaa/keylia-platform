"use client";

import { Mic, Play, Pause } from "lucide-react";
import { useState, useRef } from "react";

interface Voice {
  voiceId: string;
  name: string;
  label: string;
  previewUrl: string | null;
  category: string;
}

interface VoiceSelectorProps {
  voices: Voice[];
  selectedVoiceId: string | null;
  onSelect: (voiceId: string) => void;
  isLoading?: boolean;
}

export function VoiceSelector({
  voices,
  selectedVoiceId,
  onSelect,
  isLoading = false,
}: VoiceSelectorProps) {
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handlePlayPreview = (voice: Voice) => {
    if (!voice.previewUrl) return;

    if (playingVoiceId === voice.voiceId) {
      audioRef.current?.pause();
      setPlayingVoiceId(null);
    } else {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const audio = new Audio(voice.previewUrl);
      audioRef.current = audio;
      audio.play();
      setPlayingVoiceId(voice.voiceId);
      audio.onended = () => setPlayingVoiceId(null);
    }
  };

  const getLabelDisplay = (label: string) => {
    const parts = label.split("_");
    return parts.map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(" ");
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-700">Narration Voice</label>
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-20 bg-gray-100 rounded-lg animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!voices || voices.length === 0) {
    return (
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-700">Narration Voice</label>
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-700">
            Unable to load voices. Please refresh the page or try again later.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-gray-700">Narration Voice</label>
      <div className="grid grid-cols-2 gap-3">
        {voices.map((voice) => (
          <button
            key={voice.voiceId}
            type="button"
            onClick={() => onSelect(voice.voiceId)}
            className={`relative flex items-center gap-3 p-3 rounded-lg border-2 transition-all text-left ${
              selectedVoiceId === voice.voiceId
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300 bg-white"
            }`}
          >
            <div
              className={`flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center ${
                selectedVoiceId === voice.voiceId
                  ? "bg-blue-500 text-white"
                  : "bg-gray-100 text-gray-500"
              }`}
            >
              <Mic className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0">
              <p
                className={`font-medium truncate ${
                  selectedVoiceId === voice.voiceId
                    ? "text-blue-700"
                    : "text-gray-900"
                }`}
              >
                {voice.name}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {getLabelDisplay(voice.label)}
              </p>
            </div>
            {voice.previewUrl && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handlePlayPreview(voice);
                }}
                className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center transition-colors ${
                  playingVoiceId === voice.voiceId
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                }`}
              >
                {playingVoiceId === voice.voiceId ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </button>
            )}
            {selectedVoiceId === voice.voiceId && (
              <div className="absolute top-1 right-1 h-3 w-3 rounded-full bg-blue-500" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
