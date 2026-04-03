"use server";

import { revalidatePath } from "next/cache";

function inferenceUrl(): string {
  const base =
    process.env.VERCEL_URL != null
      ? `https://${process.env.VERCEL_URL}`
      : (process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000");
  return `${base.replace(/\/$/, "")}/api/inference/run`;
}

export async function runScoringAction(): Promise<{
  success: boolean;
  message: string;
  output?: string;
}> {
  const secret = process.env.INFERENCE_API_SECRET;
  if (process.env.VERCEL && !secret) {
    return {
      success: false,
      message:
        "Server misconfiguration: set INFERENCE_API_SECRET in Vercel environment variables.",
    };
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (secret) {
    headers.Authorization = `Bearer ${secret}`;
  }

  let res: Response;
  try {
    res = await fetch(inferenceUrl(), {
      method: "POST",
      headers,
      cache: "no-store",
    });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return {
      success: false,
      message: `Could not reach Python inference route: ${msg}`,
      output:
        "Use `vercel dev` from the web/ folder for local testing (Next.js alone does not run Python routes).",
    };
  }

  const text = await res.text();
  let body: Record<string, unknown> = {};
  try {
    body = JSON.parse(text) as Record<string, unknown>;
  } catch {
    body = { raw: text };
  }

  if (!res.ok) {
    return {
      success: false,
      message: `Inference HTTP ${res.status}`,
      output:
        typeof body.error === "string"
          ? body.error
          : text.slice(0, 4000) || undefined,
    };
  }

  if (body.ok !== true) {
    return {
      success: false,
      message: "Inference reported failure",
      output:
        typeof body.error === "string" ? body.error : JSON.stringify(body),
    };
  }

  revalidatePath("/warehouse/priority");

  const lines = [
    typeof body.message === "string" ? body.message : "",
    body.updated != null ? `updated: ${String(body.updated)}` : "",
    body.training_rows != null
      ? `training_rows: ${String(body.training_rows)}`
      : "",
  ].filter(Boolean);

  return {
    success: true,
    message: "Scoring executed successfully.",
    output: lines.join("\n"),
  };
}
