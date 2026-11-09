"use client";

import { useEffect, useRef, useState, Suspense } from "react";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { Upload, Sparkles, PlayCircle, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { Panel } from "@/components/ui";
import { analyzeCode, fetchDemoProject, ApiError } from "@/lib/api";
import { useAnalysis } from "@/lib/store";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const STEPS = [
  "Parsing AST...",
  "Calculating structural metrics...",
  "Detecting risky functions...",
  "Generating XAI explanations...",
];

const PLACEHOLDER = `def calculate_discount(order, user, code):
    if code:
        if code == "SAVE10":
            return order.total * 0.9
    return order.total
`;

function AnalyzePageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { setCurrent } = useAnalysis();

  const [code, setCode] = useState(PLACEHOLDER);
  const [filename, setFilename] = useState("example.py");
  const [analyzing, setAnalyzing] = useState(false);
  const [stepIndex, setStepIndex] = useState(-1);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (params.get("demo") === "1") {
      loadDemo(params.get("sample") || "orders");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadDemo(sample: string = "orders") {
    setError(null);
    try {
      const demo = await fetchDemoProject(sample);
      setCode(demo.code);
      setFilename(demo.filename);
    } catch {
      setError("Could not load the demo project. Is the backend running?");
    }
  }

  function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const supported = [".py", ".js", ".ts", ".java", ".cpp", ".c"];
    if (!supported.some((ext) => file.name.endsWith(ext))) {
      setError("Unsupported file type. Try .py, .js, .ts, .java, .cpp or .c.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setCode(String(reader.result || ""));
      setFilename(file.name);
      setError(null);
    };
    reader.readAsText(file);
  }

  async function handleAnalyze() {
    if (!code.trim()) {
      setError("There's no code to analyze yet — paste or upload something first.");
      return;
    }
    setError(null);
    setAnalyzing(true);
    setStepIndex(0);

    const stepTimer = setInterval(() => {
      setStepIndex((i) => (i < STEPS.length - 1 ? i + 1 : i));
    }, 550);

    const started = Date.now();
    try {
      const result = await analyzeCode(code, filename);
      const elapsed = Date.now() - started;
      const minDuration = STEPS.length * 550 + 300;
      if (elapsed < minDuration) {
        await new Promise((r) => setTimeout(r, minDuration - elapsed));
      }
      setCurrent(result, code);
      router.push("/dashboard/results");
    } catch (e) {
      const message =
        e instanceof ApiError ? e.message : "Something went wrong while analyzing this file.";
      setError(message);
      setAnalyzing(false);
      setStepIndex(-1);
    } finally {
      clearInterval(stepTimer);
    }
  }

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-50">New Analysis</h1>
        <p className="text-slate-500 mt-1 text-sm">
          Paste Python code, upload a file, or load the demo project.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Panel className="overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-slate-800/70">
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".py,.js,.ts,.java,.cpp,.c"
                  className="hidden"
                  onChange={handleUpload}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-300 border border-slate-700 rounded-lg px-3 py-1.5 hover:border-slate-500 hover:bg-slate-800/40 transition-colors"
                >
                  <Upload size={13} /> Upload File
                </button>
                <button
                  onClick={() => loadDemo("orders")}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-300 border border-slate-700 rounded-lg px-3 py-1.5 hover:border-slate-500 hover:bg-slate-800/40 transition-colors"
                >
                  <Sparkles size={13} /> Load Demo Project
                </button>
                <button
                  onClick={() => loadDemo("health")}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-300 border border-slate-700 rounded-lg px-3 py-1.5 hover:border-slate-500 hover:bg-slate-800/40 transition-colors"
                >
                  <Sparkles size={13} /> Single-function sample
                </button>
              </div>
              <div className="text-xs text-slate-500 mono">{filename}</div>
            </div>

            <div className="h-[480px]">
              <MonacoEditor
                height="100%"
                defaultLanguage="python"
                language="python"
                theme="vs-dark"
                value={code}
                onChange={(v) => setCode(v || "")}
                options={{
                  fontSize: 13,
                  minimap: { enabled: false },
                  padding: { top: 16 },
                  scrollBeyondLastLine: false,
                }}
              />
            </div>

            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800/70">
              <div className="text-xs text-slate-500">
                MVP support: Python is fully analyzed today; other languages accept
                upload but are not yet scored.
              </div>
              <button
                onClick={handleAnalyze}
                disabled={analyzing}
                className="inline-flex items-center gap-2 bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 font-medium rounded-xl px-5 py-2.5 hover:brightness-110 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {analyzing ? <Loader2 size={16} className="animate-spin" /> : <PlayCircle size={16} />}
                {analyzing ? "Analyzing..." : "Analyze Code"}
              </button>
            </div>
          </Panel>

          {error && (
            <div className="mt-4 flex items-start gap-2.5 text-sm text-red-300 bg-red-500/10 border border-red-500/25 rounded-xl px-4 py-3">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              {error}
            </div>
          )}
        </div>

        <div>
          <Panel className="p-5 sticky top-20">
            <div className="text-sm font-medium text-slate-200 mb-4">Analysis Pipeline</div>
            <div className="space-y-3">
              {STEPS.map((step, i) => {
                const done = analyzing && stepIndex > i;
                const activeStep = analyzing && stepIndex === i;
                return (
                  <div key={step} className="flex items-center gap-3 text-sm">
                    {done ? (
                      <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                    ) : activeStep ? (
                      <Loader2 size={16} className="text-cyan-400 animate-spin shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-slate-700 shrink-0" />
                    )}
                    <span
                      className={
                        done
                          ? "text-slate-300"
                          : activeStep
                          ? "text-cyan-300"
                          : "text-slate-600"
                      }
                    >
                      {String(i + 1).padStart(2, "0")} {step}
                    </span>
                  </div>
                );
              })}
            </div>
            {!analyzing && (
              <p className="text-xs text-slate-600 mt-5 leading-relaxed">
                Structural analysis runs deterministically first — the AI only
                explains metrics that have already been calculated.
              </p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={null}>
      <AnalyzePageInner />
    </Suspense>
  );
}
