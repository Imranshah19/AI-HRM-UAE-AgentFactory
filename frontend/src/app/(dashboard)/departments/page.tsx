'use client';

import { Building2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

export default function DepartmentsPage() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
      <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center mb-4">
        <Building2 className="w-8 h-8 text-blue-600" />
      </div>
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Departments</h1>
      <p className="text-slate-500 max-w-sm mb-6">
        Department management is coming soon. For now, departments can be
        managed through the Employees section.
      </p>
      <Button variant="outline" onClick={() => router.push('/employees')}>
        Go to Employees
      </Button>
    </div>
  );
}
