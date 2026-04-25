'use client';

import { useState, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Camera, Save, KeyRound, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';

import { Button }   from '@/components/ui/button';
import { Input }    from '@/components/ui/input';
import { Label }    from '@/components/ui/label';
import { Badge }    from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn }            from '@/lib/utils';
import { getInitials }   from '@/lib/utils';
import { useAuthStore }  from '@/stores/authStore';
import { api }           from '@/lib/api';

// ─── Schemas ──────────────────────────────────────────────────────────────────

const profileSchema = z.object({
  first_name: z.string().min(1, 'Required'),
  last_name:  z.string().min(1, 'Required'),
  email:      z.string().email('Invalid email'),
  phone:      z.string().optional(),
});
type ProfileFormValues = z.infer<typeof profileSchema>;

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Required'),
  new_password:     z.string().min(8, 'Minimum 8 characters'),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});
type PasswordFormValues = z.infer<typeof passwordSchema>;

// ─── Activity Log ─────────────────────────────────────────────────────────────

interface ActivityEntry {
  id:         string;
  action:     string;
  detail:     string;
  created_at: string;
  ip:         string;
}

const MOCK_ACTIVITY: ActivityEntry[] = [
  { id: '1', action: 'Login',          detail: 'Successful login',                    created_at: '2026-03-24 09:12', ip: '192.168.1.10' },
  { id: '2', action: 'Profile Update', detail: 'Updated personal information',        created_at: '2026-03-23 14:35', ip: '192.168.1.10' },
  { id: '3', action: 'Password Change',detail: 'Password changed successfully',       created_at: '2026-03-20 11:00', ip: '192.168.1.10' },
  { id: '4', action: 'Login',          detail: 'Successful login',                    created_at: '2026-03-20 08:59', ip: '192.168.1.22' },
  { id: '5', action: 'Logout',         detail: 'User logged out',                     created_at: '2026-03-19 18:30', ip: '192.168.1.22' },
  { id: '6', action: 'Report Export',  detail: 'Exported Payroll Report (Mar 2026)',  created_at: '2026-03-18 15:00', ip: '192.168.1.10' },
];

const ACTION_COLOR: Record<string, string> = {
  Login:          'bg-green-100 text-green-700',
  Logout:         'bg-slate-100 text-slate-500',
  'Password Change': 'bg-amber-100 text-amber-700',
  'Profile Update':  'bg-blue-100 text-blue-700',
  'Report Export':   'bg-purple-100 text-purple-700',
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const user    = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);

  const [activeTab, setActiveTab] = useState<'profile' | 'password' | 'activity'>('profile');
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew,     setShowNew]     = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);

  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user?.first_name ?? '',
      last_name:  user?.last_name  ?? '',
      email:      user?.email      ?? '',
      phone:      '',
    },
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: '', new_password: '', confirm_password: '' },
  });

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function onSaveProfile(values: ProfileFormValues) {
    setSavingProfile(true);
    try {
      const res = await api.patch('/api/v1/users/me', values);
      if (user) setUser({ ...user, ...res.data });
      toast.success('Profile updated');
    } catch {
      toast.error('Failed to update profile');
    } finally {
      setSavingProfile(false);
    }
  }

  async function onChangePassword(values: PasswordFormValues) {
    setSavingPassword(true);
    try {
      await api.post('/api/v1/auth/change-password', {
        current_password: values.current_password,
        new_password:     values.new_password,
      });
      toast.success('Password changed successfully');
      passwordForm.reset();
    } catch {
      toast.error('Failed to change password — check your current password');
    } finally {
      setSavingPassword(false);
    }
  }

  async function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await api.post('/api/v1/users/me/avatar', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      if (user) setUser({ ...user, avatar_url: res.data.avatar_url });
      toast.success('Photo updated');
    } catch {
      toast.error('Failed to upload photo');
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-5">
            <div className="relative group">
              <Avatar className="w-20 h-20">
                <AvatarImage src={user?.avatar_url ?? undefined} alt={user?.full_name} />
                <AvatarFallback className="bg-hrms-100 text-hrms-700 text-2xl font-bold">
                  {user ? getInitials(user.full_name) : '?'}
                </AvatarFallback>
              </Avatar>
              <button
                onClick={() => fileRef.current?.click()}
                className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="Change photo"
              >
                <Camera className="h-5 w-5 text-white" />
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleAvatarChange}
              />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 truncate">
                {user?.full_name ?? '—'}
              </h1>
              <p className="text-sm text-slate-500">{user?.email}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge className="bg-hrms-100 text-hrms-700 text-xs">{user?.roles?.[0]?.name ?? 'User'}</Badge>
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <ShieldCheck className="h-3 w-3" />
                  Account active
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tab strip */}
      <div className="flex gap-1 border-b border-slate-200">
        {([
          { id: 'profile',  label: 'Personal Info' },
          { id: 'password', label: 'Change Password' },
          { id: 'activity', label: 'Activity Log' },
        ] as const).map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === id
                ? 'border-hrms-600 text-hrms-600'
                : 'border-transparent text-slate-500 hover:text-slate-700',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Profile tab */}
      {activeTab === 'profile' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Personal Information</CardTitle>
            <CardDescription className="text-xs">Update your name, email, and contact details.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={profileForm.handleSubmit(onSaveProfile)} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs">First Name *</Label>
                  <Input className="h-9 text-sm" {...profileForm.register('first_name')} />
                  {profileForm.formState.errors.first_name && (
                    <p className="text-xs text-red-500">{profileForm.formState.errors.first_name.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Last Name *</Label>
                  <Input className="h-9 text-sm" {...profileForm.register('last_name')} />
                  {profileForm.formState.errors.last_name && (
                    <p className="text-xs text-red-500">{profileForm.formState.errors.last_name.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Email Address *</Label>
                  <Input className="h-9 text-sm" type="email" {...profileForm.register('email')} />
                  {profileForm.formState.errors.email && (
                    <p className="text-xs text-red-500">{profileForm.formState.errors.email.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Phone Number</Label>
                  <Input className="h-9 text-sm" type="tel" {...profileForm.register('phone')} />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <Button
                  type="submit"
                  disabled={savingProfile}
                  className="bg-hrms-600 hover:bg-hrms-700 text-white gap-2"
                >
                  <Save className="h-4 w-4" />
                  {savingProfile ? 'Saving…' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Password tab */}
      {activeTab === 'password' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <KeyRound className="h-4 w-4" /> Change Password
            </CardTitle>
            <CardDescription className="text-xs">
              Choose a strong password with at least 8 characters.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={passwordForm.handleSubmit(onChangePassword)} className="space-y-4 max-w-sm">
              {/* Current password */}
              <div className="space-y-1.5">
                <Label className="text-xs">Current Password *</Label>
                <div className="relative">
                  <Input
                    className="h-9 text-sm pr-10"
                    type={showCurrent ? 'text' : 'password'}
                    {...passwordForm.register('current_password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrent((v) => !v)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {passwordForm.formState.errors.current_password && (
                  <p className="text-xs text-red-500">{passwordForm.formState.errors.current_password.message}</p>
                )}
              </div>

              {/* New password */}
              <div className="space-y-1.5">
                <Label className="text-xs">New Password *</Label>
                <div className="relative">
                  <Input
                    className="h-9 text-sm pr-10"
                    type={showNew ? 'text' : 'password'}
                    {...passwordForm.register('new_password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNew((v) => !v)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {passwordForm.formState.errors.new_password && (
                  <p className="text-xs text-red-500">{passwordForm.formState.errors.new_password.message}</p>
                )}
              </div>

              {/* Confirm password */}
              <div className="space-y-1.5">
                <Label className="text-xs">Confirm New Password *</Label>
                <div className="relative">
                  <Input
                    className="h-9 text-sm pr-10"
                    type={showConfirm ? 'text' : 'password'}
                    {...passwordForm.register('confirm_password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((v) => !v)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {passwordForm.formState.errors.confirm_password && (
                  <p className="text-xs text-red-500">{passwordForm.formState.errors.confirm_password.message}</p>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  type="submit"
                  disabled={savingPassword}
                  className="bg-hrms-600 hover:bg-hrms-700 text-white gap-2"
                >
                  <KeyRound className="h-4 w-4" />
                  {savingPassword ? 'Updating…' : 'Update Password'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Activity tab */}
      {activeTab === 'activity' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Recent Activity</CardTitle>
            <CardDescription className="text-xs">Your last 30 days of account activity.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100">
              {MOCK_ACTIVITY.map((entry) => (
                <div key={entry.id} className="flex items-center gap-3 px-5 py-3">
                  <Badge
                    className={cn(
                      'text-xs shrink-0 min-w-[90px] justify-center',
                      ACTION_COLOR[entry.action] ?? 'bg-slate-100 text-slate-500',
                    )}
                  >
                    {entry.action}
                  </Badge>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-700 truncate">{entry.detail}</p>
                    <p className="text-xs text-slate-400">IP: {entry.ip}</p>
                  </div>
                  <p className="text-xs text-slate-400 shrink-0">{entry.created_at}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
