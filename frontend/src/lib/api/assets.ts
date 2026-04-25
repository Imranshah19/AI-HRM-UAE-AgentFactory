/**
 * AI-HRMS — Asset Management API calls.
 */

import { api } from '@/lib/api';
import type {
  Asset,
  AssetAssignment,
  AssetAssignmentRequest,
  AssetCreate,
  AssetFilterParams,
  AssetListResponse,
  AssetReturnRequest,
  AssetUpdate,
} from '@/types/assets';

function buildParams(f: Partial<AssetFilterParams>): URLSearchParams {
  const p = new URLSearchParams();
  if (f.category  !== undefined && f.category  !== null) p.set('category',  f.category);
  if (f.status    !== undefined && f.status    !== null) p.set('status',     f.status);
  if (f.assigned  !== undefined && f.assigned  !== null) p.set('assigned',   String(f.assigned));
  if (f.search)                                          p.set('search',     f.search);
  if (f.page)                                            p.set('page',       String(f.page));
  if (f.page_size)                                       p.set('page_size',  String(f.page_size));
  return p;
}

export async function getAssets(filters: Partial<AssetFilterParams> = {}): Promise<AssetListResponse> {
  const res = await api.get<AssetListResponse>(`/api/v1/assets?${buildParams(filters)}`);
  return res.data;
}

export async function getAsset(id: string): Promise<Asset> {
  const res = await api.get<Asset>(`/api/v1/assets/${id}`);
  return res.data;
}

export async function createAsset(data: AssetCreate): Promise<Asset> {
  const res = await api.post<Asset>('/api/v1/assets', data);
  return res.data;
}

export async function updateAsset(id: string, data: AssetUpdate): Promise<Asset> {
  const res = await api.patch<Asset>(`/api/v1/assets/${id}`, data);
  return res.data;
}

export async function assignAsset(id: string, data: AssetAssignmentRequest): Promise<AssetAssignment> {
  const res = await api.post<AssetAssignment>(`/api/v1/assets/${id}/assign`, data);
  return res.data;
}

export async function returnAsset(id: string, data: AssetReturnRequest): Promise<AssetAssignment> {
  const res = await api.post<AssetAssignment>(`/api/v1/assets/${id}/return`, data);
  return res.data;
}

export async function getEmployeeAssets(employeeId: string): Promise<Asset[]> {
  const res = await api.get<Asset[]>(`/api/v1/assets/employee/${employeeId}`);
  return res.data;
}

export async function getAssetHistory(id: string): Promise<AssetAssignment[]> {
  const res = await api.get<AssetAssignment[]>(`/api/v1/assets/${id}/history`);
  return res.data;
}
