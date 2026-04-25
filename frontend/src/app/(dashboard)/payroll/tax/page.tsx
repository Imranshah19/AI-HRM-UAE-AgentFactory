'use client';

import { FileText } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

export default function TaxCompliancePage() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
      <div className="w-16 h-16 rounded-2xl bg-emerald-50 flex items-center justify-center mb-4">
        <FileText className="w-8 h-8 text-emerald-600" />
      </div>
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Tax &amp; Compliance</h1>
      <p className="text-slate-500 max-w-sm mb-6">
        Tax computation and compliance reporting is coming soon. Payroll
        summaries are available in the main Payroll section.
      </p>
      <Button variant="outline" onClick={() => router.push('/payroll')}>
        Go to Payroll
      </Button>
    </div>
  );
}
