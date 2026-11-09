import { AnalyzeResponse, ModelDetail, ProjectRow, RepoReport, RunRow } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function analyzeCode(
  code: string,
  filename: string,
  language: string = "python"
): Promise<AnalyzeResponse> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, filename, language }),
    });
  } catch {
    throw new ApiError(
      "Can't reach the CodeReviewX backend. Make sure it's running (see README) at " + BASE,
      0
    );
  }

  if (!res.ok) {
    let detail = "Analysis failed.";
    try {
      const body = await res.json();
      const d = body.detail;
      detail = typeof d === "string" ? d : d?.message ? `${d.message}${d.line ? ` (line ${d.line})` : ""}` : detail;
    } catch {
      // ignore
    }
    throw new ApiError(detail, res.status);
  }

  return res.json();
}

export async function fetchDemoProject(sample = "orders"): Promise<{ filename: string; code: string }> {
  const res = await fetch(`${BASE}/demo?sample=${sample}`);
  if (!res.ok) throw new ApiError("Could not load demo project.", res.status);
  return res.json();
}

export async function fetchEngineStatus(): Promise<Record<string, string>> {
  try {
    const res = await fetch(`${BASE}/health`);
    if (!res.ok) throw new Error();
    return res.json();
  } catch {
    return {
      structural_scanner: "offline",
      ai_engine: "offline",
      analysis_api: "offline",
    };
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("Can't reach the CodeReviewX backend at " + BASE, 0);
  }
  if (!res.ok) {
    let msg = "Request failed.";
    try {
      const d = (await res.json()).detail;
      msg = typeof d === "string" ? d : d?.message ?? msg;
    } catch {
      // ignore
    }
    throw new ApiError(msg, res.status);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const listHistory = (projectId?: number) => request<RunRow[]>(`/history${projectId ? `?project_id=${projectId}` : ""}`);
export const openRun = <T = AnalyzeResponse>(id: number) => request<T>(`/history/${id}`);
export const deleteRun = (id: number) => request<void>(`/history/${id}`, { method: "DELETE" });
export const listProjects = () => request<ProjectRow[]>("/projects");
export const createProject = (name: string, description = "") =>
  request<ProjectRow>("/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, description }) });
export const deleteProject = (id: number) => request<void>(`/projects/${id}`, { method: "DELETE" });
export const fetchModel = () => request<ModelDetail>("/model");
export function analyzeZip(file: File, projectId?: number) {
  const fd = new FormData();
  fd.append("file", file);
  if (projectId) fd.append("project_id", String(projectId));
  return request<RepoReport>("/analyze/zip", { method: "POST", body: fd });
}
export const analyzeGithub = (url: string, projectId?: number) =>
  request<RepoReport>("/analyze/github", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url, project_id: projectId ?? null }) });
