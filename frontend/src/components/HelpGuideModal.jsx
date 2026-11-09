import React, { useState } from 'react';
import {
  Sparkles, CheckCircle2, Flame, Bot, Clock, ShieldCheck,
  ArrowRight, X, Layers, Activity, HelpCircle, Play
} from 'lucide-react';

const GUIDE_STEPS = [
  {
    step: 1,
    title: 'Noise Reduction & Correlation',
    tag: 'HOURS OF LOGS → 1.8 SECONDS',
    icon: Layers,
    color: 'text-[#00f0ff]',
    borderColor: 'border-[#00f0ff]/40',
    bgColor: 'bg-cyan-950/20',
    description: 'On-call engineers are inundated with alert storms. J.A.R.V.I.S. ingests heterogeneous metrics, logs, and traces, mines Drain3 patterns, and uses weighted topological clustering to collapse 47+ cascading alerts into 1 coherent incident in under 2 seconds.',
    actionPrompt: 'Click "CORRELATE (47 → 1)" in the top HUD bar to see the noise reduction in action.'
  },
  {
    step: 2,
    title: 'Deterministic Root Cause & Time Machine',
    tag: 'ZERO LLM IN THE CAUSAL LOOP',
    icon: Activity,
    color: 'text-amber-400',
    borderColor: 'border-amber-500/40',
    bgColor: 'bg-amber-950/20',
    description: 'The root cause is derived mathematically from 6 causal features: Onset Rank, Upstream Leaf Status, Downstream Coverage, Reverse PageRank Random Walk, and Resource/Deploy Evidence. Drag the Incident Time Machine slider to replay how the failure spread from database to gateway.',
    actionPrompt: 'Inspect the Root Cause verdict card and drag the time slider below the graph.'
  },
  {
    step: 3,
    title: 'Live Counterfactual Proof',
    tag: 'PROVE IT, DON\'T GUESS',
    icon: CheckCircle2,
    color: 'text-emerald-400',
    borderColor: 'border-emerald-500/40',
    bgColor: 'bg-emerald-950/20',
    description: 'Other tools tell you what is red. J.A.R.V.I.S. proves its hypothesis: clicking "Verify Fix" actively heals the candidate service in the simulator and streams real-time telemetry confirming downstream error rates fall to 0% across all dependencies.',
    actionPrompt: 'Click "VERIFY FIX" in the top bar to watch the cascade clear with 100% recovery.'
  },
  {
    step: 4,
    title: 'Chaos Lab & Grounded War Room',
    tag: 'JUDGE INTERACTIVE PLAYGROUND',
    icon: Flame,
    color: 'text-[#ff3366]',
    borderColor: 'border-[#ff3366]/40',
    bgColor: 'bg-red-950/20',
    description: 'Inject live unscripted failures from the Chaos Lab (Kill DB, Memory Leak, Bad Deploy, Stripe 503, or "Surprise Me"). Switch to the AI War Room to ask questions like "Why did you blame the DB?" with answers strictly bound to cite verified [EVT-xxx] evidence chips.',
    actionPrompt: 'Pick any fault in the Chaos Lab, then query the Grounded War Room chat.'
  }
];

export default function HelpGuideModal({ isOpen, onClose }) {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const current = GUIDE_STEPS[currentStep];
  const StepIcon = current.icon;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-[#0b101d] border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#080d19]">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-[#00f0ff]/10 border border-[#00f0ff]/40">
              <HelpCircle className="w-5 h-5 text-[#00f0ff]" />
            </div>
            <div>
              <div className="font-mono font-bold text-sm text-slate-100 tracking-wider">
                J.A.R.V.I.S. OPERATOR'S GUIDE // INTERACTIVE TOUR
              </div>
              <div className="text-[11px] font-mono text-slate-400">
                Step {currentStep + 1} of {GUIDE_STEPS.length}: {current.title}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Progress Indicator Bar */}
        <div className="flex h-1 bg-slate-900">
          {GUIDE_STEPS.map((s, idx) => (
            <div
              key={idx}
              className={`flex-1 transition-all duration-300 ${
                idx <= currentStep ? 'bg-[#00f0ff]' : 'bg-slate-800'
              }`}
            />
          ))}
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          <div className={`p-4 rounded-xl border ${current.borderColor} ${current.bgColor} transition-all`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <StepIcon className={`w-5 h-5 ${current.color}`} />
                <span className={`text-xs font-mono font-bold ${current.color}`}>
                  {current.title}
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-400 bg-black/40 px-2 py-0.5 rounded border border-slate-800">
                {current.tag}
              </span>
            </div>

            <p className="text-xs font-sans text-slate-300 leading-relaxed mb-3">
              {current.description}
            </p>

            <div className="flex items-center space-x-2 bg-black/50 p-2.5 rounded-lg border border-slate-800/80">
              <Play className="w-3.5 h-3.5 text-[#00f0ff] shrink-0" />
              <span className="text-[11px] font-mono text-[#00f0ff]">
                {current.actionPrompt}
              </span>
            </div>
          </div>

          {/* Step Selector Pills */}
          <div className="grid grid-cols-4 gap-2 pt-2">
            {GUIDE_STEPS.map((s, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentStep(idx)}
                className={`p-2 rounded-lg border text-left transition-all ${
                  idx === currentStep
                    ? 'border-[#00f0ff] bg-cyan-950/40 text-slate-100'
                    : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <div className="text-[10px] font-mono text-slate-500">0{s.step}</div>
                <div className="text-[11px] font-bold font-mono truncate">{s.title.split(' ')[0]}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-800 bg-[#080d19]">
          <button
            onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
            disabled={currentStep === 0}
            className="text-xs font-mono text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-all px-3 py-1.5 rounded"
          >
            Previous
          </button>

          <div className="flex items-center space-x-2">
            {currentStep < GUIDE_STEPS.length - 1 ? (
              <button
                onClick={() => setCurrentStep(prev => Math.min(GUIDE_STEPS.length - 1, prev + 1))}
                className="flex items-center space-x-1.5 text-xs font-mono font-bold bg-[#00f0ff] hover:bg-[#38bdf8] text-black px-4 py-2 rounded-lg transition-all"
              >
                <span>Next Feature</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={onClose}
                className="flex items-center space-x-1.5 text-xs font-mono font-bold bg-emerald-400 hover:bg-emerald-300 text-black px-4 py-2 rounded-lg transition-all shadow-lg shadow-emerald-950"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Start Exploring</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
