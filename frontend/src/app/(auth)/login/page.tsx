'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Loader2, Brain, Users, BarChart3, Shield } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import { loginUser, extractApiError } from '@/lib/auth';
import { useAuthStore } from '@/stores/authStore';

// ─── Validation schema ────────────────────────────────────────────────────────

const loginSchema = z.object({
  email:      z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password:   z.string().min(6, 'Password must be at least 6 characters'),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

// ─── Feature highlights (left panel) ─────────────────────────────────────────

const FEATURES = [
  {
    icon:  Brain,
    title: 'AI-Powered Insights',
    desc:  'Smart attrition prediction, CV scoring, and workforce analytics.',
  },
  {
    icon:  Users,
    title: 'Complete HR Suite',
    desc:  'Employees, attendance, leave, payroll and recruitment — all in one place.',
  },
  {
    icon:  BarChart3,
    title: 'Real-Time Reporting',
    desc:  'Live dashboards, Excel exports and automated regulatory reports.',
  },
  {
    icon:  Shield,
    title: 'Enterprise Security',
    desc:  'Multi-tenant RBAC, audit trails, and SOC-2 ready infrastructure.',
  },
] as const;

// ─── Component ────────────────────────────────────────────────────────────────

function LoginForm() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const setUser      = useAuthStore((s) => s.setUser);

  const [showPassword, setShowPassword] = useState(false);
  const [isShaking,    setIsShaking]    = useState(false);
  const [serverError,  setServerError]  = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', rememberMe: false },
  });

  // ── Submit ──────────────────────────────────────────────────────────────────

  async function onSubmit(data: LoginFormData) {
    setServerError('');
    try {
      const user = await loginUser(data.email, data.password);
      setUser(user);
      toast.success(`Welcome back, ${user.first_name}!`);

      const from = searchParams.get('from');
      router.replace(from && from !== '/login' ? from : '/dashboard');
    } catch (error: unknown) {
      const msg = extractApiError(error);
      setServerError(msg);

      // Shake the card on credential error
      setIsShaking(true);
      setTimeout(() => setIsShaking(false), 600);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Shake keyframe — injected inline to avoid modifying tailwind.config */}
      <style>{`
        @keyframes shake {
          0%,100% { transform: translateX(0); }
          15%,45%,75% { transform: translateX(-7px); }
          30%,60%,90% { transform: translateX(7px); }
        }
        .animate-shake { animation: shake 0.5s ease-in-out; }
      `}</style>

      <div className="flex min-h-screen">
        {/* ── Left branding panel (hidden on mobile) ─────────────────────── */}
        <div className="hidden lg:flex lg:w-1/2 xl:w-3/5 bg-gradient-to-br from-hrms-700 via-hrms-800 to-hrms-950 flex-col justify-between p-12 text-white relative overflow-hidden">
          {/* Background decoration */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full translate-y-1/2 -translate-x-1/2" />
          </div>

          {/* Logo */}
          <div className="relative z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <div>
                <span className="text-2xl font-bold tracking-tight">AI-HRMS</span>
                <p className="text-hrms-200 text-xs">Human Resource Management System</p>
              </div>
            </div>
          </div>

          {/* Hero text */}
          <div className="relative z-10 space-y-6">
            <h1 className="text-4xl xl:text-5xl font-bold leading-tight">
              AI-Powered HR
              <br />
              <span className="text-hrms-200">Management</span>
            </h1>
            <p className="text-hrms-100 text-lg max-w-md leading-relaxed">
              Streamline every HR process — from hiring to retirement — with
              intelligent automation and real-time insights.
            </p>

            {/* Feature list */}
            <div className="grid gap-4 pt-2">
              {FEATURES.map(({ icon: Icon, title, desc }) => (
                <div key={title} className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Icon className="w-4 h-4 text-hrms-200" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm text-white">{title}</p>
                    <p className="text-hrms-200 text-xs leading-relaxed">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <p className="relative z-10 text-hrms-300 text-xs">
            © {new Date().getFullYear()} AI-HRMS. Enterprise Edition.
          </p>
        </div>

        {/* ── Right login panel ───────────────────────────────────────────── */}
        <div className="w-full lg:w-1/2 xl:w-2/5 flex items-center justify-center p-6 sm:p-10 bg-white dark:bg-slate-900">
          <div
            className={cn(
              'w-full max-w-md space-y-8',
              isShaking && 'animate-shake',
            )}
          >
            {/* Mobile logo */}
            <div className="flex items-center gap-2 lg:hidden">
              <div className="w-9 h-9 bg-hrms-600 rounded-xl flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-hrms-700">AI-HRMS</span>
            </div>

            {/* Header */}
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50">
                Sign in to your account
              </h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                This system is invite-only.{' '}
                <span className="text-slate-400">Contact your HR administrator for access.</span>
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
              {/* Email */}
              <div className="space-y-1.5">
                <Label htmlFor="email">Work email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  placeholder="admin@hrms.com"
                  disabled={isSubmitting}
                  aria-invalid={!!errors.email}
                  {...register('email')}
                  className={cn(errors.email && 'border-red-400 focus-visible:ring-red-400')}
                />
                {errors.email && (
                  <p className="text-xs text-red-500">{errors.email.message}</p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link
                    href="/forgot-password"
                    className="text-xs text-hrms-600 hover:text-hrms-700 hover:underline"
                    tabIndex={-1}
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    disabled={isSubmitting}
                    aria-invalid={!!errors.password}
                    {...register('password')}
                    className={cn(
                      'pr-10',
                      errors.password && 'border-red-400 focus-visible:ring-red-400',
                    )}
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-xs text-red-500">{errors.password.message}</p>
                )}
              </div>

              {/* Remember me */}
              <div className="flex items-center gap-2">
                <Checkbox id="rememberMe" {...register('rememberMe')} />
                <Label
                  htmlFor="rememberMe"
                  className="text-sm text-slate-600 dark:text-slate-400 cursor-pointer font-normal"
                >
                  Keep me signed in
                </Label>
              </div>

              {/* Server error */}
              {serverError && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 dark:bg-red-950/30 dark:border-red-900 dark:text-red-400">
                  {serverError}
                </div>
              )}

              {/* Submit */}
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-hrms-600 hover:bg-hrms-700 text-white h-11 text-sm font-medium"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </form>

            {/* Footer note */}
            <p className="text-center text-xs text-slate-400">
              By signing in you agree to our{' '}
              <span className="underline cursor-pointer hover:text-slate-600">Privacy Policy</span>
              {' '}and{' '}
              <span className="underline cursor-pointer hover:text-slate-600">Terms of Service</span>.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
