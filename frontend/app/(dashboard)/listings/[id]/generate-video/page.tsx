"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Video, Loader2 } from "lucide-react";
import Link from "next/link";
import { trpc } from "@/lib/trpc/client";
import {
  DurationSelector,
  VoiceSelector,
  StyleSelector,
  ModelSelector,
  type VideoModelType,
} from "@/components/tour-video";

export default function GenerateVideoPage() {
  const params = useParams();
  const router = useRouter();
  const listingId = params.id as string;

  // Form state
  const [duration, setDuration] = useState<"15" | "30" | "60">("30");
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(null);
  const [tone, setTone] = useState<"luxury" | "cozy" | "modern" | "minimal" | "bold">("modern");
  const [pace, setPace] = useState<"slow" | "moderate" | "fast">("moderate");
  const [videoModel, setVideoModel] = useState<VideoModelType>("kling_v2");
  const [isGenerating, setIsGenerating] = useState(false);

  // Get listing data
  const { data: listing, isLoading: listingLoading } = trpc.listing.get.useQuery(
    { id: listingId },
    { enabled: !!listingId }
  );

  // Get available voices
  const { data: voices, isLoading: voicesLoading } = trpc.tourVideo.getVoices.useQuery();

  // Set default voice when voices load
  useEffect(() => {
    if (voices && voices.length > 0 && !selectedVoiceId) {
      setSelectedVoiceId(voices[0].voiceId);
    }
  }, [voices, selectedVoiceId]);

  // Generate mutation
  const generateMutation = trpc.tourVideo.generateFromListing.useMutation({
    onSuccess: (data) => {
      // Navigate to progress page
      router.push(`/listings/${listingId}/generate-video/${data.projectId}`);
    },
    onError: (error) => {
      setIsGenerating(false);
      alert(error.message);
    },
  });

  const handleGenerate = () => {
    setIsGenerating(true);
    generateMutation.mutate({
      listingId,
      duration,
      voiceSettings: {
        voice_id: selectedVoiceId || undefined,
        language: "en-US",
        style: "professional",
        gender: "female",
      },
      styleSettings: {
        tone,
        pace,
        video_model: videoModel,
      },
    });
  };

  if (listingLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <p className="text-gray-500">Listing not found</p>
        <Link href="/listings" className="text-blue-500 hover:underline mt-2">
          Back to listings
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <Link
            href={`/listings/${listingId}`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to listing
          </Link>
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Video className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                Generate Tour Video
              </h1>
              <p className="text-sm text-gray-500">{listing.address}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border p-6 space-y-8">
          {/* Listing Preview */}
          <div className="flex gap-4 p-4 bg-gray-50 rounded-lg">
            {listing.photos && listing.photos[0] && (
              <img
                src={listing.photos[0]}
                alt="Property"
                className="h-24 w-24 object-cover rounded-lg"
              />
            )}
            <div>
              <h3 className="font-medium text-gray-900">{listing.address}</h3>
              <p className="text-sm text-gray-500">
                {listing.city}, {listing.state} {listing.zip}
              </p>
              <p className="text-sm text-gray-700 mt-1">
                {listing.bedrooms} bed • {listing.bathrooms} bath •{" "}
                {listing.sqft?.toLocaleString()} sqft
              </p>
              <p className="text-lg font-semibold text-blue-600 mt-1">
                ${listing.price?.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Photo Count */}
          {listing.photos && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-sm text-blue-700">
                <span className="font-medium">{listing.photos.length} photos</span>{" "}
                will be used to create your tour video
              </p>
            </div>
          )}

          {/* Duration Selection */}
          <DurationSelector value={duration} onChange={setDuration} />

          {/* Voice Selection */}
          <VoiceSelector
            voices={voices || []}
            selectedVoiceId={selectedVoiceId}
            onSelect={setSelectedVoiceId}
            isLoading={voicesLoading}
          />

          {/* Style Selection */}
          <StyleSelector
            tone={tone}
            pace={pace}
            onToneChange={setTone}
            onPaceChange={setPace}
          />

          {/* Video Model Selection */}
          <ModelSelector
            value={videoModel}
            onChange={setVideoModel}
          />

          {/* Generate Button */}
          <div className="pt-4 border-t">
            <button
              onClick={handleGenerate}
              disabled={isGenerating || !selectedVoiceId}
              className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Starting Generation...
                </>
              ) : (
                <>
                  <Video className="h-5 w-5" />
                  Generate Tour Video
                </>
              )}
            </button>
            <p className="text-center text-sm text-gray-500 mt-3">
              This will take 2-5 minutes depending on video length
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
