'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Brain, ArrowLeft, Loader2, MailCheck } from 'lucide-react';

import { Button }  from '@/components/ui/button';
import { Input }   from '@/components/ui/input';
import { Label }   from '@/components/ui/label';
import { cn }      from '@/lib/utils';

const schema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
});
type FormData = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    // Backend endpoint not yet implemented — simulate success
    await new Promise((r) => setTimeout(r, 800));
    setSubmittedEmail(data.email);
    setSubmitted(true);
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center gap-2 mb-10">
          <div className="w-9 h-9 bg-hrms-600 rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-hrms-700">AI-HRMS</span>
        </div>

        {submitted ? (
          /* ── Success state ──────────────────────────────────────────────── */
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-200 dark:border-slate-800 p-8 text-center space-y-4">
            <div className="w-14 h-14 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto">
              <MailCheck className="w-7 h-7 text-green-600 dark:text-green-400" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50">
              Check your inbox
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              If an account exists for{' '}
              <span className="font-medium text-slate-700 dark:text-slate-300">
                {submittedEmail}
              </span>
              , we've sent password reset instructions.
            </p>
            <p className="text-xs text-slate-400">
              Didn't receive it? Check your spam folder or contact your HR administrator.
            </p>
            <Link href="/login">
              <Button variant="outline" className="w-full mt-2">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to login
              </Button>
            </Link>
          </div>
        ) : (
          /* ── Form state ─────────────────────────────────────────────────── */
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-card border border-slate-200 dark:border-slate-800 p-8 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">
                Reset your password
              </h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Enter your work email and we'll send you a reset link.
              </p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="email">Work email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  placeholder="you@company.ai-hrms.com"
                  disabled={isSubmitting}
                  {...register('email')}
                  className={cn(errors.email && 'border-red-400 focus-visible:ring-red-400')}
                />
                {errors.email && (
                  <p className="text-xs text-red-500">{errors.email.message}</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-hrms-600 hover:bg-hrms-700 text-white h-11"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending…
                  </>
                ) : (
                  'Send reset link'
                )}
              </Button>
            </form>

            <Link
              href="/login"
              className="flex items-center justify-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
