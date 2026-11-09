"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { AnalyzeResponse, HistoryEntry } from "./types";

interface AnalysisContextValue {
  current: AnalyzeResponse | null;
  currentCode: string;
  history: HistoryEntry[];
  selectedFunction: string | null;
  setSelectedFunction: (name: string | null) => void;
  setCurrent: (result: AnalyzeResponse, code: string) => void;
  loadFromHistory: (id: string) => void;
  clearHistory: () => void;
}

function worstOf(r: AnalyzeResponse): string | null {
  return r?.summary?.worst_function ?? r?.graph?.nodes?.[0]?.id ?? null;
}

const AnalysisContext = createContext<AnalysisContextValue | null>(null);

const HISTORY_KEY = "codereviewx.history";
const CURRENT_KEY = "codereviewx.current";

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [current, setCurrentState] = useState<AnalyzeResponse | null>(null);
  const [currentCode, setCurrentCode] = useState<string>("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [selectedFunction, setSelectedFunction] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const storedHistory = localStorage.getItem(HISTORY_KEY);
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time localStorage hydration on mount
      if (storedHistory) setHistory((JSON.parse(storedHistory) as HistoryEntry[]).filter((h) => h?.result?.factors?.[0]?.what));
      const storedCurrent = localStorage.getItem(CURRENT_KEY);
      if (storedCurrent) {
        const parsed = JSON.parse(storedCurrent);
        if (parsed.result?.factors?.[0]?.what) {
          setCurrentState(parsed.result);
          setCurrentCode(parsed.code);
        }
        if (parsed.result?.summary && parsed.result?.factors?.[0]?.what && parsed.result?.graph?.nodes?.length) {
          setSelectedFunction(worstOf(parsed.result));
        }
      }
    } catch {
      // ignore corrupted storage
    }
    setHydrated(true);
  }, []);

  const setCurrent = useCallback((result: AnalyzeResponse, code: string) => {
    setCurrentState(result);
    setCurrentCode(code);
    setSelectedFunction(worstOf(result));

    try {
      localStorage.setItem(CURRENT_KEY, JSON.stringify({ result, code }));
    } catch {
      // storage full or unavailable — non-fatal
    }

    const entry: HistoryEntry = {
      id: `${Date.now()}`,
      filename: result.filename,
      date: new Date().toISOString(),
      health: result.summary.code_health,
      risk_score: result.summary.risk_score,
      functions: result.summary.functions,
      status:
        result.summary.overall_health < 50 ? "high" : result.summary.overall_health < 75 ? "medium" : "low",
      result,
      code,
    };

    setHistory((prev) => {
      const next = [entry, ...prev].slice(0, 25);
      try {
        localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const loadFromHistory = useCallback(
    (id: string) => {
      const entry = history.find((h) => h.id === id);
      if (!entry) return;
      setCurrentState(entry.result);
      setCurrentCode(entry.code);
      setSelectedFunction(worstOf(entry.result));
      try {
        localStorage.setItem(CURRENT_KEY, JSON.stringify({ result: entry.result, code: entry.code }));
      } catch {
        // ignore
      }
    },
    [history]
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(HISTORY_KEY);
    } catch {
      // ignore
    }
  }, []);

  if (!hydrated) {
    return null;
  }

  return (
    <AnalysisContext.Provider
      value={{
        current,
        currentCode,
        history,
        selectedFunction,
        setSelectedFunction,
        setCurrent,
        loadFromHistory,
        clearHistory,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const ctx = useContext(AnalysisContext);
  if (!ctx) throw new Error("useAnalysis must be used within AnalysisProvider");
  return ctx;
}
