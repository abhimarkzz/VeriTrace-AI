/**
 * VeriTrace API facade.
 *
 * Re-exports the API client, error classes, and analysis services.
 */

export * from "./api/client";
export * from "./api/analysis";

// Legacy compatibility alias
export { checkBackendHealth as isApiAvailable } from "./api/client";
