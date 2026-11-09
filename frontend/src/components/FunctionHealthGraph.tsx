"use client";

import { useMemo, useCallback } from "react";
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, MarkerType, Handle, Position, NodeProps } from "reactflow";
import "reactflow/dist/style.css";
import { AnalyzeResponse } from "@/lib/types";
import { riskColor, scoreHex } from "./ui";
import clsx from "clsx";

function HealthNode({ data }: NodeProps) {
  const color = riskColor(data.risk);
  return (
    <div
      className={clsx("rounded-xl border px-3.5 py-2.5 w-[200px] bg-[#0b0f18]/95 cursor-pointer transition-all", data.selected && "ring-2 ring-cyan-300/70 ring-offset-2 ring-offset-[#05070d]")}
      style={{
        borderColor: color,
        boxShadow: data.risk === "high" ? `0 0 0 1px ${color}66, 0 0 22px ${color}55` : data.risk === "medium" ? `0 0 14px ${color}33` : `0 0 10px ${color}22`,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-600 !border-none !w-1.5 !h-1.5" />
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-medium text-slate-100 mono truncate">{data.name}()</div>
        <div className="text-sm font-semibold" style={{ color }}>{data.health_score}</div>
      </div>
      <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500">
        <span>Cx {data.complexity}</span>
        <span>{data.lines} lines</span>
        <span>{data.issues} issues</span>
      </div>
      <div className="flex gap-[2px] mt-2">
        {(data.strip as number[]).map((s, i) => (
          <i key={i} className="h-1.5 flex-1 rounded-sm" style={{ background: scoreHex(s), opacity: s >= 90 ? 0.25 : 0.9 }} />
        ))}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-slate-600 !border-none !w-1.5 !h-1.5" />
    </div>
  );
}

const nodeTypes = { health: HealthNode };

function layers(ids: string[], edges: { source: string; target: string }[]): Record<string, number> {
  const level: Record<string, number> = Object.fromEntries(ids.map((i) => [i, 0]));
  for (let pass = 0; pass < ids.length; pass++) {
    let changed = false;
    for (const e of edges) {
      if (level[e.target] < level[e.source] + 1 && level[e.source] + 1 < ids.length) {
        level[e.target] = level[e.source] + 1;
        changed = true;
      }
    }
    if (!changed) break;
  }
  return level;
}

export default function FunctionHealthGraph({ result, selected, onSelect }: { result: AnalyzeResponse; selected: string | null; onSelect: (name: string) => void }) {
  const { graph, functions } = result;
  const nodes: Node[] = useMemo(() => {
    const linked = new Set(graph.edges.flatMap((e) => [e.source, e.target]));
    const lv = layers(graph.nodes.map((n) => n.id), graph.edges);
    const maxLevel = Math.max(0, ...Object.values(lv));
    const PER_ROW = 4;
    const fmap = Object.fromEntries(functions.map((f) => [f.name, f]));
    const pos: Record<string, { x: number; y: number }> = {};
    let row = 0;
    for (let l = 0; l <= maxLevel; l++) {
      const ids = graph.nodes.filter((n) => linked.has(n.id) && lv[n.id] === l).map((n) => n.id);
      for (let i = 0; i < ids.length; i += PER_ROW) {
        const chunk = ids.slice(i, i + PER_ROW);
        chunk.forEach((id, j) => {
          pos[id] = { x: j * 250 - (chunk.length * 250) / 2, y: row * 140 + l * 40 };
        });
        row++;
      }
    }
    const solo = graph.nodes.filter((n) => !linked.has(n.id)).map((n) => n.id);
    if (solo.length && row > 0) row += 0.4;
    for (let i = 0; i < solo.length; i += PER_ROW) {
      const chunk = solo.slice(i, i + PER_ROW);
      chunk.forEach((id, j) => {
        pos[id] = { x: j * 250 - (chunk.length * 250) / 2, y: row * 140 + 40 * (maxLevel + 1) };
      });
      row++;
    }
    return graph.nodes.map((n) => ({
      id: n.id,
      type: "health",
      position: pos[n.id],
      data: { ...n, selected: n.id === selected, strip: Object.values(fmap[n.id]?.factors ?? {}).map((c) => c.score) },
    }));
  }, [graph, functions, selected]);

  const edges: Edge[] = useMemo(
    () =>
      graph.edges.map((e, i) => ({
        id: `e-${i}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        animated: true,
        style: { stroke: "#475569", strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#64748b", width: 14, height: 14 },
      })),
    [graph.edges]
  );

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => onSelect(node.id), [onSelect]);

  return (
    <div className="h-full w-full">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodeClick={handleNodeClick} fitView fitViewOptions={{ padding: 0.2 }} proOptions={{ hideAttribution: true }} minZoom={0.2}>
        <Background color="#1a2033" gap={18} />
        <Controls className="!bg-slate-900 !border-slate-700 [&>button]:!bg-slate-900 [&>button]:!border-slate-700 [&>button]:!text-slate-300" />
        <MiniMap pannable zoomable maskColor="rgba(5,7,13,0.75)" style={{ background: "#0b0f18", border: "1px solid #1e2434" }} nodeColor={(n) => riskColor((n.data as { risk: string }).risk as "low" | "medium" | "high")} />
      </ReactFlow>
    </div>
  );
}
