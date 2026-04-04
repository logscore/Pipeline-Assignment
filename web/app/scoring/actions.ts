"use server";

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";

type InferenceResponse = {
  success?: boolean;
  message?: string;
  output?: string;
};

function getRequestOrigin(headerStore: Headers): string {
  const host =
    headerStore.get("x-forwarded-host") ?? headerStore.get("host") ?? "";

  if (!host) {
    throw new Error("Missing request host header.");
  }

  const protocol =
    headerStore.get("x-forwarded-proto") ??
    (host.includes("localhost") ? "http" : "https");

  return `${protocol}://${host}`;
}

function buildInferenceUrl(
  configuredUrl: string | undefined,
  requestOrigin: string,
) {
  const trimmedUrl = configuredUrl?.trim();

  if (trimmedUrl?.startsWith("http://") || trimmedUrl?.startsWith("https://")) {
    return new URL(trimmedUrl);
  }

  const pathname =
    !trimmedUrl || trimmedUrl.startsWith("/")
      ? trimmedUrl || "/api/inference/run"
      : `/${trimmedUrl}`;

  return new URL(pathname, requestOrigin);
}

function parseInferenceResponse(
  responseText: string,
): InferenceResponse | null {
  try {
    const parsed = JSON.parse(responseText);
    return typeof parsed === "object" && parsed !== null
      ? (parsed as InferenceResponse)
      : null;
  } catch {
    return null;
  }
}

function isVercelAuthResponse(status: number, responseText: string): boolean {
  return (
    status === 401 &&
    responseText.includes("Authentication Required") &&
    responseText.includes("Vercel")
  );
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

  const headerStore = await headers();
  const requestOrigin = getRequestOrigin(headerStore);
  const inferenceUrl = buildInferenceUrl(
    process.env.INFERENCE_FUNCTION_URL,
    requestOrigin,
  );

  const requestHeaders: Record<string, string> = {
    accept: "application/json, text/plain;q=0.9, text/html;q=0.8",
    "content-type": "application/json",
  };

  if (secret) {
    requestHeaders.Authorization = `Bearer ${secret}`;
  }

  if (process.env.INFERENCE_TRIGGER_TOKEN) {
    requestHeaders["x-inference-token"] = process.env.INFERENCE_TRIGGER_TOKEN;
  }

  if (inferenceUrl.origin === requestOrigin) {
    const cookieHeader = headerStore.get("cookie");
    if (cookieHeader) {
      requestHeaders.cookie = cookieHeader;
    }

    if (process.env.VERCEL_AUTOMATION_BYPASS_SECRET) {
      requestHeaders["x-vercel-protection-bypass"] =
        process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
    }
  }

  let res: Response;
  try {
    res = await fetch(inferenceUrl, {
      method: "POST",
      headers: requestHeaders,
      cache: "no-store",
      body: JSON.stringify({}),
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
  const parsedResponse = text ? parseInferenceResponse(text) : null;

  if (!res.ok) {
    if (isVercelAuthResponse(res.status, text)) {
      return {
        success: false,
        message:
          "Inference endpoint is protected by Vercel Deployment Protection. Use a same-origin URL or configure Protection Bypass for Automation.",
        output: text,
      };
    }

    if (res.status === 404) {
      return {
        success: false,
        message: `No inference endpoint was found at ${inferenceUrl.pathname}.`,
        output: text,
      };
    }

    return {
      success: parsedResponse?.success ?? false,
      message: parsedResponse?.message ?? `Inference HTTP ${res.status}`,
      output: parsedResponse?.output ?? text,
    };
  }

  const body = parsedResponse ?? {};

  if (body.ok !== true && body.success !== true) {
    return {
      success: false,
      message: body.message ?? "Inference reported failure",
      output: body.output ?? JSON.stringify(body),
    };
  }

  revalidatePath("/warehouse/priority");

  const lines = [body.message ? String(body.message) : ""].filter(Boolean);

  return {
    success: true,
    message: "Scoring executed successfully.",
    output: lines.join("\n") || undefined,
  };
}
