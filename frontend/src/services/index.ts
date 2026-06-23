import { createHttpService } from "./http";
import { createMockService } from "./mock";
import type { BackendService } from "./types";

// Single entrypoint for the app. Uses the real backend client by default.
// Set VITE_USE_MOCK=true to fall back to the localStorage mock implementation.
const useMock = import.meta.env.VITE_USE_MOCK === "true";

export const backend: BackendService = useMock ? createMockService() : createHttpService();
export type { BackendService } from "./types";
