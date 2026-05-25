import { CheckCircle, Circle, Loader2 } from "lucide-react";

const STEPS = [
  { id: 1, label: "Scanning communities & web sources" },
  { id: 2, label: "Running neural search" },
  { id: 3, label: "AI analyzing all data points" },
  { id: 4, label: "Generating your brief" },
];

export default function LoadingState({ statusMessages }) {
  const lastStatus = statusMessages[statusMessages.length - 1];
  const currentStep = lastStatus?.step ?? 0;

  return (
    <div className="w-full max-w-xl mx-auto animate-fade-in">
      <div className="card space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-[#7C3AED]/10 mb-4">
            <Loader2 className="h-6 w-6 text-[#7C3AED] animate-spin" />
          </div>
          <h3 className="font-semibold text-lg">Analyzing your niche...</h3>
          <p className="text-sm text-[#71717A] mt-1">This takes 20–40 seconds</p>
        </div>

        {/* Step progress */}
        <div className="space-y-3">
          {STEPS.map((step) => {
            const isDone = currentStep > step.id || (currentStep === step.id && lastStatus?.done);
            const isActive = currentStep === step.id && !lastStatus?.done;

            return (
              <div key={step.id} className="flex items-center gap-3">
                {isDone ? (
                  <CheckCircle className="h-5 w-5 text-[#10B981] flex-shrink-0" />
                ) : isActive ? (
                  <Loader2 className="h-5 w-5 text-[#7C3AED] animate-spin flex-shrink-0" />
                ) : (
                  <Circle className="h-5 w-5 text-[#1E1E24] flex-shrink-0" />
                )}
                <span
                  className={
                    isDone
                      ? "text-sm text-[#10B981]"
                      : isActive
                      ? "text-sm text-[#F4F4F5]"
                      : "text-sm text-[#71717A]"
                  }
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Live status text */}
        {lastStatus && (
          <div className="rounded-lg bg-[#0A0A0B] border border-[#1E1E24] p-3">
            <p className="text-sm text-[#71717A] font-mono">{lastStatus.message}</p>
          </div>
        )}

        {/* Progress bar */}
        <div className="h-1 w-full rounded-full bg-[#1E1E24] overflow-hidden">
          <div
            className="h-full rounded-full bg-[#7C3AED] transition-all duration-500"
            style={{ width: `${Math.min(100, (currentStep / 4) * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
