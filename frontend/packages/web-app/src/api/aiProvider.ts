/**
 * AI Provider API — manage LLM provider configurations.
 */
import http from './http'

const BASE = '/api/rpa-ai-service/v1/providers'

export interface ProviderCreate {
  name: string
  provider_type: 'deepseek' | 'openai_compatible' | 'custom' | 'maas'
  base_url: string
  api_key: string
  models?: string[]
  is_default?: boolean
  is_active?: boolean
}

export interface ProviderUpdate {
  name?: string
  provider_type?: 'deepseek' | 'openai_compatible' | 'custom' | 'maas'
  base_url?: string
  api_key?: string
  models?: string[]
  is_default?: boolean
  is_active?: boolean
}

export interface ProviderResponse {
  id: number
  name: string
  provider_type: string
  base_url: string
  api_key_display: string
  models: string[] | null
  is_default: boolean
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface TestConnectionResult {
  success: boolean
  status_code?: number
  models: string[]
  message: string
}

/**
 * List all configured AI providers.
 */
export async function getProviders(): Promise<ProviderResponse[]> {
  const res = await http.get<ProviderResponse[]>(`${BASE}`)
  return res.data || []
}

/**
 * Create a new AI provider.
 */
export async function createProvider(data: ProviderCreate): Promise<ProviderResponse> {
  const res = await http.post<ProviderResponse>(`${BASE}`, data)
  return res.data
}

/**
 * Update an existing AI provider.
 */
export async function updateProvider(id: number, data: ProviderUpdate): Promise<ProviderResponse> {
  const res = await http.put<ProviderResponse>(`${BASE}/${id}`, data)
  return res.data
}

/**
 * Delete an AI provider.
 */
export async function deleteProvider(id: number): Promise<void> {
  await http.delete(`${BASE}/${id}`)
}

/**
 * Test connection to a provider.
 */
export async function testProvider(id: number): Promise<TestConnectionResult> {
  const res = await http.post<TestConnectionResult>(`${BASE}/${id}/test`)
  return res.data
}
