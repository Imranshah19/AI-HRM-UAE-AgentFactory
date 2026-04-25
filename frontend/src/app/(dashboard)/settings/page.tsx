'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Building2, Users, ShieldCheck, Bell, Plug,
  Save, Plus, Pencil, Trash2, Check, X,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button }   from '@/components/ui/button';
import { Input }    from '@/components/ui/input';
import { Label }    from '@/components/ui/label';
import { Switch }   from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge }    from '@/components/ui/badge';
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface TenantSettings {
  company_name:     string;
  company_email:    string;
  company_phone:    string;
  company_address:  string;
  timezone:         string;
  currency:         string;
  date_format:      string;
  working_days:     string[];
  working_hours_start: string;
  working_hours_end:   string;
}

interface UserRow {
  id:         string;
  full_name:  string;
  email:      string;
  role:       string;
  is_active:  boolean;
  created_at: string;
}

interface RoleRow {
  id:          string;
  name:        string;
  description: string;
  permissions: Record<string, string[]>;
  user_count:  number;
}

// ─── Schemas ──────────────────────────────────────────────────────────────────

const companySchema = z.object({
  company_name:        z.string().min(1, 'Required'),
  company_email:       z.string().email('Invalid email'),
  company_phone:       z.string().optional(),
  company_address:     z.string().optional(),
  timezone:            z.string(),
  currency:            z.string(),
  date_format:         z.string(),
  working_hours_start: z.string(),
  working_hours_end:   z.string(),
});
type CompanyFormValues = z.infer<typeof companySchema>;

// ─── Nav ──────────────────────────────────────────────────────────────────────

type TabId = 'company' | 'users' | 'roles' | 'notifications' | 'integrations';

const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'company',       label: 'Company Settings',     icon: Building2   },
  { id: 'users',         label: 'User Management',      icon: Users       },
  { id: 'roles',         label: 'Roles & Permissions',  icon: ShieldCheck },
  { id: 'notifications', label: 'Notification Settings',icon: Bell        },
  { id: 'integrations',  label: 'Integrations',         icon: Plug        },
];

// ─── Company Settings ─────────────────────────────────────────────────────────

const TIMEZONES = ['Asia/Karachi', 'Asia/Dubai', 'UTC', 'America/New_York', 'Europe/London'];
const CURRENCIES = ['PKR', 'USD', 'EUR', 'GBP', 'AED'];
const DATE_FORMATS = ['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD'];

function CompanyTab() {
  const [loading, setLoading] = useState(false);
  const form = useForm<CompanyFormValues>({
    resolver: zodResolver(companySchema),
    defaultValues: {
      company_name: '', company_email: '', company_phone: '', company_address: '',
      timezone: 'Asia/Karachi', currency: 'PKR', date_format: 'DD/MM/YYYY',
      working_hours_start: '09:00', working_hours_end: '18:00',
    },
  });

  async function onSubmit(values: CompanyFormValues) {
    setLoading(true);
    try {
      await api.patch('/api/v1/tenants/settings', values);
      toast.success('Company settings saved');
    } catch {
      toast.error('Failed to save settings');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Company Information</CardTitle>
          <CardDescription className="text-xs">Basic company details shown on documents and emails.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs">Company Name *</Label>
              <Input className="h-8 text-sm" {...form.register('company_name')} />
              {form.formState.errors.company_name && (
                <p className="text-xs text-red-500">{form.formState.errors.company_name.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Company Email *</Label>
              <Input className="h-8 text-sm" type="email" {...form.register('company_email')} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Phone</Label>
              <Input className="h-8 text-sm" {...form.register('company_phone')} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Address</Label>
            <Input className="h-8 text-sm" {...form.register('company_address')} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Regional Settings</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <Label className="text-xs">Timezone</Label>
            <Select value={form.watch('timezone')} onValueChange={(v) => form.setValue('timezone', v)}>
              <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                {TIMEZONES.map((tz) => <SelectItem key={tz} value={tz}>{tz}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Currency</Label>
            <Select value={form.watch('currency')} onValueChange={(v) => form.setValue('currency', v)}>
              <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                {CURRENCIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Date Format</Label>
            <Select value={form.watch('date_format')} onValueChange={(v) => form.setValue('date_format', v)}>
              <SelectTrigger className="h-8 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                {DATE_FORMATS.map((f) => <SelectItem key={f} value={f}>{f}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Working Hours</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <div className="space-y-1.5">
            <Label className="text-xs">Start Time</Label>
            <Input type="time" className="h-8 text-sm w-32" {...form.register('working_hours_start')} />
          </div>
          <span className="text-slate-400 mt-5">—</span>
          <div className="space-y-1.5">
            <Label className="text-xs">End Time</Label>
            <Input type="time" className="h-8 text-sm w-32" {...form.register('working_hours_end')} />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button type="submit" disabled={loading} className="bg-hrms-600 hover:bg-hrms-700 text-white gap-2">
          <Save className="h-4 w-4" />
          {loading ? 'Saving…' : 'Save Settings'}
        </Button>
      </div>
    </form>
  );
}

// ─── User Management ──────────────────────────────────────────────────────────

const MOCK_USERS: UserRow[] = [
  { id: '1', full_name: 'Admin User', email: 'admin@company.com', role: 'Super Admin', is_active: true, created_at: '2024-01-01' },
  { id: '2', full_name: 'HR Manager', email: 'hr@company.com', role: 'HR Manager', is_active: true, created_at: '2024-01-15' },
  { id: '3', full_name: 'Payroll Officer', email: 'payroll@company.com', role: 'Payroll Officer', is_active: false, created_at: '2024-02-01' },
];

function UsersTab() {
  const [search, setSearch] = useState('');
  const filtered = MOCK_USERS.filter(
    (u) => u.full_name.toLowerCase().includes(search.toLowerCase()) ||
           u.email.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between gap-3">
        <Input
          placeholder="Search users…"
          className="h-8 text-sm max-w-xs"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Button size="sm" className="bg-hrms-600 hover:bg-hrms-700 text-white gap-1.5">
          <Plus className="h-3.5 w-3.5" /> Invite User
        </Button>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((u) => (
              <TableRow key={u.id}>
                <TableCell className="font-medium">{u.full_name}</TableCell>
                <TableCell className="text-slate-500 text-sm">{u.email}</TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-xs">{u.role}</Badge>
                </TableCell>
                <TableCell>
                  <Badge className={cn('text-xs', u.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500')}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </TableCell>
                <TableCell className="text-slate-500 text-sm">{u.created_at}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" className="h-7 w-7">
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500 hover:text-red-600">
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ─── Roles & Permissions ──────────────────────────────────────────────────────

const MODULES = ['employees', 'attendance', 'payroll', 'leave', 'recruitment', 'performance', 'training', 'assets', 'reports'];
const ACTIONS = ['read', 'create', 'update', 'delete'];

const DEFAULT_ROLES: RoleRow[] = [
  {
    id: '1', name: 'Super Admin', description: 'Full access to all modules', user_count: 1,
    permissions: Object.fromEntries(MODULES.map((m) => [m, [...ACTIONS]])),
  },
  {
    id: '2', name: 'HR Manager', description: 'Manage employees, leave, and recruitment', user_count: 2,
    permissions: {
      employees: ['read', 'create', 'update'], leave: ['read', 'create', 'update', 'delete'],
      recruitment: ['read', 'create', 'update'], attendance: ['read'], reports: ['read'],
    },
  },
  {
    id: '3', name: 'Employee', description: 'View own data only', user_count: 45,
    permissions: { attendance: ['read'], leave: ['read', 'create'], payroll: ['read'] },
  },
];

function RolesTab() {
  const [selected, setSelected] = useState<RoleRow | null>(null);

  return (
    <div className="flex gap-4 max-w-5xl">
      <div className="w-56 shrink-0 space-y-1">
        {DEFAULT_ROLES.map((r) => (
          <button
            key={r.id}
            onClick={() => setSelected(r)}
            className={cn(
              'w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors',
              selected?.id === r.id
                ? 'bg-hrms-50 text-hrms-700 font-medium'
                : 'hover:bg-slate-50 text-slate-600',
            )}
          >
            <div className="font-medium">{r.name}</div>
            <div className="text-xs text-slate-400">{r.user_count} users</div>
          </button>
        ))}
        <Button size="sm" variant="outline" className="w-full gap-1.5 mt-2">
          <Plus className="h-3.5 w-3.5" /> New Role
        </Button>
      </div>

      <div className="flex-1">
        {!selected ? (
          <div className="text-center text-slate-400 text-sm py-16">Select a role to view permissions</div>
        ) : (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-sm">{selected.name}</CardTitle>
                  <CardDescription className="text-xs">{selected.description}</CardDescription>
                </div>
                <Button size="sm" variant="outline" className="gap-1.5">
                  <Pencil className="h-3.5 w-3.5" /> Edit
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Module</TableHead>
                    {ACTIONS.map((a) => (
                      <TableHead key={a} className="text-center capitalize">{a}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {MODULES.map((mod) => (
                    <TableRow key={mod}>
                      <TableCell className="font-medium capitalize">{mod}</TableCell>
                      {ACTIONS.map((action) => {
                        const has = selected.permissions[mod]?.includes(action);
                        return (
                          <TableCell key={action} className="text-center">
                            {has
                              ? <Check className="h-4 w-4 text-green-500 mx-auto" />
                              : <X className="h-4 w-4 text-slate-200 mx-auto" />
                            }
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// ─── Notification Settings ────────────────────────────────────────────────────

interface NotifPref {
  id:      string;
  label:   string;
  desc:    string;
  email:   boolean;
  inApp:   boolean;
}

const DEFAULT_PREFS: NotifPref[] = [
  { id: 'leave_request',   label: 'Leave Requests',       desc: 'When an employee applies for leave',         email: true,  inApp: true  },
  { id: 'payroll_ready',   label: 'Payroll Processed',    desc: 'When monthly payroll run is complete',       email: true,  inApp: true  },
  { id: 'new_hire',        label: 'New Employee Joined',  desc: 'When a new employee is onboarded',           email: false, inApp: true  },
  { id: 'birthday',        label: 'Employee Birthdays',   desc: 'Upcoming employee birthdays',                email: false, inApp: true  },
  { id: 'asset_return',    label: 'Asset Return Overdue', desc: 'Assets not returned after offboarding',      email: true,  inApp: true  },
  { id: 'job_application', label: 'New Applications',     desc: 'When a candidate applies to an open role',   email: true,  inApp: true  },
];

function NotificationsTab() {
  const [prefs, setPrefs] = useState<NotifPref[]>(DEFAULT_PREFS);

  function toggle(id: string, field: 'email' | 'inApp') {
    setPrefs((prev) => prev.map((p) => p.id === id ? { ...p, [field]: !p[field] } : p));
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <p className="text-sm text-slate-500">Configure which events trigger email or in-app notifications.</p>
      <Card>
        <CardContent className="divide-y divide-slate-100 p-0">
          {prefs.map((p) => (
            <div key={p.id} className="flex items-center justify-between px-5 py-3.5">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-700">{p.label}</p>
                <p className="text-xs text-slate-400">{p.desc}</p>
              </div>
              <div className="flex items-center gap-6 ml-4 shrink-0">
                <div className="flex flex-col items-center gap-0.5">
                  <span className="text-xs text-slate-400">Email</span>
                  <Switch checked={p.email} onCheckedChange={() => toggle(p.id, 'email')} />
                </div>
                <div className="flex flex-col items-center gap-0.5">
                  <span className="text-xs text-slate-400">In-App</span>
                  <Switch checked={p.inApp} onCheckedChange={() => toggle(p.id, 'inApp')} />
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
      <div className="flex justify-end">
        <Button
          size="sm"
          className="bg-hrms-600 hover:bg-hrms-700 text-white gap-2"
          onClick={() => toast.success('Notification preferences saved')}
        >
          <Save className="h-3.5 w-3.5" /> Save Preferences
        </Button>
      </div>
    </div>
  );
}

// ─── Integrations ─────────────────────────────────────────────────────────────

interface Integration {
  id:          string;
  name:        string;
  description: string;
  connected:   boolean;
  logo:        string;
}

const INTEGRATIONS: Integration[] = [
  { id: 'slack',    name: 'Slack',         description: 'Send HR notifications to Slack channels',              connected: false, logo: '💬' },
  { id: 'google',   name: 'Google Workspace', description: 'Sync employee directory with Google',               connected: false, logo: '🔵' },
  { id: 'biometric',name: 'Biometric Device', description: 'Pull attendance logs from biometric hardware',      connected: false, logo: '🔐' },
  { id: 'email',    name: 'SMTP Email',    description: 'Configure outgoing email server',                       connected: true,  logo: '📧' },
  { id: 'payslip',  name: 'PaySlip PDF',   description: 'Customize payslip PDF template',                       connected: true,  logo: '📄' },
];

function IntegrationsTab() {
  const [integrations, setIntegrations] = useState<Integration[]>(INTEGRATIONS);

  function toggle(id: string) {
    setIntegrations((prev) => prev.map((i) => i.id === id ? { ...i, connected: !i.connected } : i));
    toast.success('Integration updated');
  }

  return (
    <div className="space-y-3 max-w-2xl">
      {integrations.map((int) => (
        <Card key={int.id}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="text-2xl w-10 text-center shrink-0">{int.logo}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-slate-700">{int.name}</p>
                <Badge
                  className={cn(
                    'text-xs',
                    int.connected ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500',
                  )}
                >
                  {int.connected ? 'Connected' : 'Not connected'}
                </Badge>
              </div>
              <p className="text-xs text-slate-400">{int.description}</p>
            </div>
            <Button
              size="sm"
              variant={int.connected ? 'outline' : 'default'}
              className={cn(!int.connected && 'bg-hrms-600 hover:bg-hrms-700 text-white')}
              onClick={() => toggle(int.id)}
            >
              {int.connected ? 'Disconnect' : 'Connect'}
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('company');

  const TAB_CONTENT: Record<TabId, React.ComponentType> = {
    company:       CompanyTab,
    users:         UsersTab,
    roles:         RolesTab,
    notifications: NotificationsTab,
    integrations:  IntegrationsTab,
  };
  const ActiveContent = TAB_CONTENT[activeTab];

  return (
    <div className="max-w-screen-xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Settings</h1>

      <div className="flex gap-6">
        {/* Sidebar nav */}
        <aside className="w-52 shrink-0 hidden lg:block">
          <nav className="space-y-0.5">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-left',
                  activeTab === id
                    ? 'bg-hrms-50 text-hrms-700 font-medium dark:bg-hrms-950/30 dark:text-hrms-300'
                    : 'text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Mobile tabs */}
        <div className="lg:hidden flex gap-1 overflow-x-auto pb-1 w-full">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap transition-colors',
                activeTab === id
                  ? 'bg-hrms-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 min-w-0">
          <ActiveContent />
        </div>
      </div>
    </div>
  );
}
