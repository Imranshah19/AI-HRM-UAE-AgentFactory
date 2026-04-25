'use client';

/**
 * AI-HRMS — Asset Management TanStack Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as assetsApi      from '@/lib/api/assets';
import { extractApiError } from '@/lib/auth';
import type {
  AssetAssignmentRequest,
  AssetCreate,
  AssetFilterParams,
  AssetReturnRequest,
  AssetUpdate,
} from '@/types/assets';

export const assetKeys = {
  list:        (f: Partial<AssetFilterParams>) => ['assets', f] as const,
  detail:      (id: string)                    => ['asset', id] as const,
  history:     (id: string)                    => ['asset-history', id] as const,
  employee:    (empId: string)                 => ['employee-assets', empId] as const,
};

export function useAssets(filters: Partial<AssetFilterParams> = {}) {
  return useQuery({
    queryKey:        assetKeys.list(filters),
    queryFn:         () => assetsApi.getAssets(filters),
    staleTime:       15_000,
    placeholderData: (prev) => prev,
  });
}

export function useAsset(id: string) {
  return useQuery({
    queryKey: assetKeys.detail(id),
    queryFn:  () => assetsApi.getAsset(id),
    enabled:  !!id,
  });
}

export function useAssetHistory(id: string) {
  return useQuery({
    queryKey: assetKeys.history(id),
    queryFn:  () => assetsApi.getAssetHistory(id),
    enabled:  !!id,
  });
}

export function useEmployeeAssets(employeeId: string) {
  return useQuery({
    queryKey: assetKeys.employee(employeeId),
    queryFn:  () => assetsApi.getEmployeeAssets(employeeId),
    enabled:  !!employeeId,
  });
}

export function useCreateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AssetCreate) => assetsApi.createAsset(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
      toast.success('Asset created');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useUpdateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AssetUpdate }) =>
      assetsApi.updateAsset(id, data),
    onSuccess: (asset) => {
      qc.invalidateQueries({ queryKey: ['assets'] });
      qc.invalidateQueries({ queryKey: assetKeys.detail(asset.id) });
      toast.success('Asset updated');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useAssignAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AssetAssignmentRequest }) =>
      assetsApi.assignAsset(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
      qc.invalidateQueries({ queryKey: ['employee-assets'] });
      toast.success('Asset assigned successfully');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}

export function useReturnAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AssetReturnRequest }) =>
      assetsApi.returnAsset(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
      qc.invalidateQueries({ queryKey: ['employee-assets'] });
      toast.success('Asset returned successfully');
    },
    onError: (err) => toast.error(extractApiError(err)),
  });
}
