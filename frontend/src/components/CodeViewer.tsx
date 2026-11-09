"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef } from "react";
import type { OnMount } from "@monaco-editor/react";
import { AnalyzeResponse, IssueOut } from "@/lib/types";
import { Panel } from "./ui";

type Ed = Parameters<OnMount>[0];
type Monaco = Parameters<OnMount>[1];
type Collection = ReturnType<Ed["createDecorationsCollection"]>;
type Deco = NonNullable<Parameters<Ed["createDecorationsCollection"]>[0]>[number];

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

export default function CodeViewer({ code, result, selectedFunction, issue }: { code: string; result: AnalyzeResponse; selectedFunction: string | null; issue: IssueOut | null }) {
  const editorRef = useRef<Ed | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const collRef = useRef<Collection | null>(null);

  function apply() {
    const ed = editorRef.current;
    const monaco = monacoRef.current;
    if (!ed || !monaco) return;
    const fn = result.functions.find((f) => f.name === selectedFunction);
    const decos: Deco[] = [];
    if (fn) {
      decos.push({
        range: new monaco.Range(fn.line_start, 1, fn.line_end, 1),
        options: { isWholeLine: true, className: "crx-fn-line", linesDecorationsClassName: fn.risk === "high" ? "crx-gutter-high" : fn.risk === "medium" ? "crx-gutter-med" : "crx-gutter-low" },
      });
    }
    if (issue) {
      for (const ln of issue.lines) {
        decos.push({ range: new monaco.Range(ln, 1, ln, 1), options: { isWholeLine: true, className: issue.severity === "critical" ? "crx-issue-line-critical" : "crx-issue-line" } });
      }
    }
    collRef.current?.clear();
    collRef.current = ed.createDecorationsCollection(decos);
    const target = issue?.line_start ?? fn?.line_start;
    if (target) ed.revealLineInCenter(target);
  }

  useEffect(() => {
    apply();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFunction, issue, code, result]);

  return (
    <Panel className="overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 text-xs text-slate-400">
        <span className="mono">{result.filename}</span>
        <span>
          {issue ? `Highlighting ${issue.id}: ${issue.title} (lines ${issue.lines.slice(0, 6).join(", ")})` : selectedFunction ? `Selected: ${selectedFunction}()` : "Select a function or finding"}
        </span>
      </div>
      <div className="h-[460px]">
        <MonacoEditor
          height="100%"
          language="python"
          theme="vs-dark"
          value={code}
          onMount={(ed, monaco) => {
            editorRef.current = ed;
            monacoRef.current = monaco;
            apply();
          }}
          options={{ readOnly: true, minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false, glyphMargin: false, lineDecorationsWidth: 6 }}
        />
      </div>
    </Panel>
  );
}
