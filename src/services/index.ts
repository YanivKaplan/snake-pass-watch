import { createMockService } from "./mock";
import type { BackendService } from "./types";

// Single entrypoint for the app. Swap implementation here to wire a real backend.
export const backend: BackendService = createMockService();
export type { BackendService } from "./types";
