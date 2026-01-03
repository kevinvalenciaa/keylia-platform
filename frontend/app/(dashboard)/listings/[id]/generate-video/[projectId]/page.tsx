"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, XCircle, RefreshCw } from "lucide-react";
import { trpc } from "@/lib/trpc/client";
import { GenerationProgress, VideoPlayer } from "@/components/tour-video";

export default function VideoProgressPage() {
  const params = useParams();
  const router = useRouter();
  const listingId = params.id as string;
  const projectId = params.projectId as string;

  const [isPolling, setIsPolling] = useState(true);

  // Get progress
  const {
    data: progress,
    isLoading,
    refetch,
  } = trpc.tourVideo.getProgress.useQuery(
    { projectId },
    {
      enabled: !!projectId,
      refetchInterval: isPolling ? 3000 : false, // Poll every 3 seconds
    }
  );

  // Get preview data when completed
  const { data: preview } = trpc.tourVideo.getPreview.useQuery(
    { projectId },
    {
      enabled: progress?.status === "completed",
    }
  );

  // Stop polling when completed or failed
  useEffect(() => {
    if (progress?.status === "completed" || progress?.status === "failed") {
      setIsPolling(false);
    }
  }, [progress?.status]);

  // Cancel mutation
  const cancelMutation = trpc.tourVideo.cancel.useMutation({
    onSuccess: () => {
      router.push(`/listings/${listingId}`);
    },
  });

  const handleCancel = () => {
    if (confirm("Are you sure you want to cancel video generation?")) {
      cancelMutation.mutate({ projectId });
    }
  };

  const handleRetry = () => {
    router.push(`/listings/${listingId}/generate-video`);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-pulse text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!progress) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
        <p className="text-gray-500">Project not found</p>
        <Link
          href={`/listings/${listingId}`}
          className="text-blue-500 hover:underline mt-2"
        >
          Back to listing
        </Link>
      </div>
    );
  }

  const isComplete = progress.status === "completed";
  const isFailed = progress.status === "failed";
  const isProcessing = progress.status === "processing" || progress.status === "queued";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <Link
            href={`/listings/${listingId}`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to listing
          </Link>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border p-6">
          {/* Title */}
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-gray-900">
              {isComplete
                ? "Your Tour Video is Ready!"
                : isFailed
                ? "Video Generation Failed"
                : "Generating Your Tour Video"}
            </h1>
            <p className="text-gray-500 mt-1">
              {isComplete
                ? "Download or share your video below"
                : isFailed
                ? "Something went wrong during generation"
                : "Please wait while we create your video"}
            </p>
          </div>

          {/* Progress or Result */}
          {isProcessing && (
            <div className="space-y-6">
              <GenerationProgress
                status={progress.status}
                progressPercent={progress.progressPercent}
                currentStep={progress.currentStep}
                stepDetails={progress.stepDetails as Record<string, any>}
                estimatedRemainingSeconds={progress.estimatedRemainingSeconds}
                errorMessage={progress.errorMessage}
              />

              {/* Cancel Button */}
              <div className="pt-4 border-t">
                <button
                  onClick={handleCancel}
                  className="flex items-center gap-2 text-gray-500 hover:text-red-600 transition-colors"
                >
                  <XCircle className="h-4 w-4" />
                  Cancel Generation
                </button>
              </div>
            </div>
          )}

          {isFailed && (
            <div className="space-y-6">
              <GenerationProgress
                status={progress.status}
                progressPercent={progress.progressPercent}
                currentStep={progress.currentStep}
                stepDetails={progress.stepDetails as Record<string, any>}
                estimatedRemainingSeconds={null}
                errorMessage={progress.errorMessage}
              />

              {/* Retry Button */}
              <div className="pt-4 border-t flex gap-3">
                <button
                  onClick={handleRetry}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </button>
                <Link
                  href={`/listings/${listingId}`}
                  className="px-4 py-2 text-gray-600 hover:text-gray-900"
                >
                  Back to Listing
                </Link>
              </div>
            </div>
          )}

          {isComplete && progress.outputUrl && (
            <VideoPlayer
              videoUrl={progress.outputUrl}
              title={preview?.title || "Tour Video"}
              caption={preview?.generated_caption}
              hashtags={preview?.generated_hashtags}
            />
          )}
        </div>

        {/* Script Preview (when completed) */}
        {isComplete && preview?.generated_script && (
          <div className="mt-6 bg-white rounded-xl shadow-sm border p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Generated Script
            </h2>
            <div className="space-y-4">
              {/* Hook */}
              {(preview.generated_script as any).hook && (
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm font-medium text-blue-700">Hook</p>
                  <p className="text-gray-700 mt-1">
                    {(preview.generated_script as any).hook}
                  </p>
                </div>
              )}

              {/* Scenes */}
              {(preview.generated_script as any).scenes && (
                <div className="space-y-2">
                  {((preview.generated_script as any).scenes as any[]).map(
                    (scene: any, index: number) => (
                      <div key={index} className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-sm font-medium text-gray-500">
                          Scene {scene.scene_number || index + 1}
                        </p>
                        <p className="text-gray-700 mt-1">{scene.narration}</p>
                      </div>
                    )
                  )}
                </div>
              )}

              {/* CTA */}
              {(preview.generated_script as any).cta && (
                <div className="p-3 bg-green-50 rounded-lg">
                  <p className="text-sm font-medium text-green-700">
                    Call to Action
                  </p>
                  <p className="text-gray-700 mt-1">
                    {(preview.generated_script as any).cta}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
