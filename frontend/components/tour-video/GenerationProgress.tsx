"use client";

import { CheckCircle2, Circle, Loader2, XCircle, Video, Mic, FileText, Wand2 } from "lucide-react";
import { motion } from "framer-motion";

interface StepStatus {
  status: string;
  completed?: number;
  total?: number;
}

interface GenerationProgressProps {
  status: string;
  progressPercent: number;
  currentStep: string | null;
  stepDetails: Record<string, StepStatus>;
  estimatedRemainingSeconds: number | null;
  errorMessage: string | null;
}

const steps = [
  { key: "script", label: "Generating Script", icon: FileText },
  { key: "voiceover", label: "Creating Voiceover", icon: Mic },
  { key: "videos", label: "Generating Videos", icon: Video },
  { key: "composition", label: "Compositing", icon: Wand2 },
];

export function GenerationProgress({
  status,
  progressPercent,
  currentStep,
  stepDetails,
  estimatedRemainingSeconds,
  errorMessage,
}: GenerationProgressProps) {
  const getStepStatus = (stepKey: string) => {
    const detail = stepDetails[stepKey];
    if (!detail) return "pending";
    return detail.status;
  };

  const getStepIcon = (stepKey: string) => {
    const stepStatus = getStepStatus(stepKey);
    const step = steps.find((s) => s.key === stepKey);
    const Icon = step?.icon || Circle;

    if (stepStatus === "completed") {
      return <CheckCircle2 className="h-6 w-6 text-green-500" />;
    }
    if (stepStatus === "in_progress") {
      return <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />;
    }
    if (status === "failed") {
      return <XCircle className="h-6 w-6 text-red-500" />;
    }
    return <Icon className="h-6 w-6 text-gray-300" />;
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

  return (
    <div className="space-y-6">
      {/* Overall Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">
            {status === "completed"
              ? "Complete!"
              : status === "failed"
              ? "Generation Failed"
              : "Generating your tour video..."}
          </span>
          <span className="font-medium text-gray-900">{progressPercent}%</span>
        </div>
        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${
              status === "failed"
                ? "bg-red-500"
                : status === "completed"
                ? "bg-green-500"
                : "bg-blue-500"
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
        {estimatedRemainingSeconds && status === "processing" && (
          <p className="text-sm text-gray-500">
            Estimated time remaining: {formatTime(estimatedRemainingSeconds)}
          </p>
        )}
      </div>

      {/* Step-by-step Progress */}
      <div className="space-y-4">
        {steps.map((step, index) => {
          const stepStatus = getStepStatus(step.key);
          const isActive = step.key === currentStep;
          const detail = stepDetails[step.key] as StepStatus | undefined;

          return (
            <div
              key={step.key}
              className={`flex items-center gap-4 p-4 rounded-lg transition-colors ${
                isActive
                  ? "bg-blue-50 border border-blue-200"
                  : stepStatus === "completed"
                  ? "bg-green-50 border border-green-200"
                  : "bg-gray-50 border border-gray-100"
              }`}
            >
              <div className="flex-shrink-0">{getStepIcon(step.key)}</div>
              <div className="flex-1 min-w-0">
                <p
                  className={`font-medium ${
                    isActive
                      ? "text-blue-700"
                      : stepStatus === "completed"
                      ? "text-green-700"
                      : "text-gray-500"
                  }`}
                >
                  {step.label}
                </p>
                {step.key === "videos" && detail && detail.total && (
                  <p className="text-sm text-gray-500">
                    Scene {detail.completed || 0} of {detail.total}
                  </p>
                )}
              </div>
              {stepStatus === "completed" && (
                <span className="text-sm text-green-600 font-medium">Done</span>
              )}
              {isActive && stepStatus !== "completed" && (
                <span className="text-sm text-blue-600 font-medium">
                  In Progress
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-800">Generation Failed</p>
              <p className="text-sm text-red-600 mt-1">{errorMessage}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
