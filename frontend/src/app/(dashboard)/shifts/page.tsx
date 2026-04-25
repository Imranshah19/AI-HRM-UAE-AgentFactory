'use client';

import { Timer } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

export default function ShiftsPage() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
      <div className="w-16 h-16 rounded-2xl bg-violet-50 flex items-center justify-center mb-4">
        <Timer className="w-8 h-8 text-violet-600" />
      </div>
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Shift Management</h1>
      <p className="text-slate-500 max-w-sm mb-6">
        Shift scheduling and management is coming soon. For now, attendance
        records can be viewed in the Attendance section.
      </p>
      <Button variant="outline" onClick={() => router.push('/attendance')}>
        Go to Attendance
      </Button>
    </div>
  );
}
