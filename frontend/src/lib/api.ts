import type { QueryResponse } from "../types/query";

export async function queryProcurement(question: string): Promise<QueryResponse> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${base}/api/query`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
  if (!response.ok) throw new Error("查詢服務暫時無法使用");
  return response.json();
}
