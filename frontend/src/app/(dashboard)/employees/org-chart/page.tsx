'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, RefreshCw } from 'lucide-react';

import { Button }         from '@/components/ui/button';
import { OrgChartView }   from '@/components/employees/OrgChartView';
import { useOrgChart }    from '@/hooks/useEmployees';

export default function OrgChartPage() {
  const router  = useRouter();
  const { data: nodes = [], isLoading, isError, refetch, isFetching } = useOrgChart();
  const [, setSelected] = useState<string | null>(null);

  function handleSelect(id: string) {
    setSelected(id);
    router.push(`/employees/${id}`);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-white dark:bg-slate-950">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-hrms-600" />
          <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            Organisation Chart
          </h1>
          {nodes.length > 0 && (
            <span className="text-xs text-slate-400 ml-1">
              Click any card to open profile
            </span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-1.5"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-auto bg-slate-50 dark:bg-slate-900/50">
        {isLoading ? (
          <div className="flex items-center justify-center h-full py-20">
            <div className="flex flex-col items-center gap-3 text-slate-400">
              <div className="h-8 w-8 border-2 border-hrms-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm">Loading org chart…</p>
            </div>
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <Users className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm mb-3">Failed to load org chart.</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>Try again</Button>
          </div>
        ) : (
          <OrgChartView nodes={nodes} onSelect={handleSelect} />
        )}
      </div>
    </div>
  );
}
