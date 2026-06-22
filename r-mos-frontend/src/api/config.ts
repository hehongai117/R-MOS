/**
 * Single source of truth for API base URL constants.
 *
 * This module has no intra-project imports so it can be safely imported by
 * both `api/client.ts` and `store/authStore.ts` without creating a circular
 * dependency.
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
export const API_ROOT = `${API_BASE_URL}/api/v1`
