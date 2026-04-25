'use client';

import { useState, useEffect } from 'react';
import {
  Monitor, Plus, Search, RefreshCw, Laptop, Smartphone,
  Truck, Armchair, MoreHorizontal, UserCheck, RotateCcw,
  Package, AlertTriangle, CheckCircle, XCircle,
} from 'lucide-react';

import { Button }    from '@/components/ui/button';
import { Badge }     from '@/components/ui/badge';
import { Input }     from '@/components/ui/input';
import { Label }     from '@/components/ui/label';
import { Textarea }  from '@/components/ui/textarea';
import {
  Card, CardContent,
} from '@/components/ui/card';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import {
  useAssets,
  useCreateAsset,
  useUpdateAsset,
  useAssignAsset,
  useReturnAsset,
  useAssetHistory,
} from '@/hooks/useAssets';

import type {
  AssetListItem,
  AssetCreate,
  AssetCategory,
  AssetCondition,
  AssetStatus,
  AssetFilterParams,
} from '@/types/assets';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<AssetStatus, string> = {
  available:   'bg-green-50  text-green-700  border-green-200',
  assigned:    'bg-blue-50   text-blue-700   border-blue-200',
  maintenance: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  retired:     'bg-slate-100 text-slate-500  border-slate-200',
  lost:        'bg-red-50    text-red-600    border-red-200',
  disposed:    'bg-gray-100  text-gray-500   border-gray-200',
};

const CONDITION_COLORS: Record<AssetCondition, string> = {
  excellent: 'text-green-600',
  good:      'text-blue-600',
  fair:      'text-amber-600',
  poor:      'text-orange-600',
  damaged:   'text-red-600',
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  laptop:     <Laptop     className="h-4 w-4" />,
  desktop:    <Monitor    className="h-4 w-4" />,
  mobile:     <Smartphone className="h-4 w-4" />,
  vehicle:    <Truck      className="h-4 w-4" />,
  furniture:  <Armchair   className="h-4 w-4" />,
};

const CATEGORIES: AssetCategory[] = [
  'laptop','desktop','mobile','tablet','monitor','keyboard','mouse',
  'headset','sim_card','access_card','vehicle','furniture','other',
];
const CONDITIONS: AssetCondition[] = ['excellent','good','fair','poor','damaged'];

// ─── Stats ────────────────────────────────────────────────────────────────────

function AssetStats({ total, assigned, available, maintenance }: {
  total: number; assigned: number; available: number; maintenance: number;
}) {
  const cards = [
    { label: 'Total Assets',  value: total,       icon: Package,      color: 'text-blue-600',   bg: 'bg-blue-50'   },
    { label: 'Assigned',      value: assigned,     icon: UserCheck,    color: 'text-green-600',  bg: 'bg-green-50'  },
    { label: 'Available',     value: available,    icon: CheckCircle,  color: 'text-emerald-600',bg: 'bg-emerald-50'},
    { label: 'Maintenance',   value: maintenance,  icon: AlertTriangle,color: 'text-amber-600',  bg: 'bg-amber-50'  },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map(({ label, value, icon: Icon, color, bg }) => (
        <Card key={label}>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="text-2xl font-bold mt-0.5">{value}</p>
              </div>
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${bg}`}>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Add / Edit Asset Dialog ──────────────────────────────────────────────────

function AssetFormDialog({
  open,
  onClose,
  initial,
}: {
  open:     boolean;
  onClose:  () => void;
  initial?: AssetListItem;
}) {
  const createAsset = useCreateAsset();
  const updateAsset = useUpdateAsset();
  const isEdit      = !!initial;

  const [form, setForm] = useState<AssetCreate>({
    name:          initial?.name          ?? '',
    category:      (initial?.category     ?? 'laptop') as AssetCategory,
    brand:         initial?.brand         ?? '',
    condition:     (initial?.condition    ?? 'good')   as AssetCondition,
    serial_number: null,
    purchase_cost: null,
    warranty_expiry: initial?.warranty_expiry ?? null,
    location:      null,
    notes:         null,
  });

  function set(k: keyof AssetCreate, v: unknown) {
    setForm((p) => ({ ...p, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isEdit && initial) {
      await updateAsset.mutateAsync({ id: initial.id, data: form });
    } else {
      await createAsset.mutateAsync(form);
    }
    onClose();
  }

  const isPending = createAsset.isPending || updateAsset.isPending;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Asset' : 'Add New Asset'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 space-y-1">
              <Label>Asset Name *</Label>
              <Input
                required
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                placeholder="e.g. MacBook Pro 14"
              />
            </div>
            <div className="space-y-1">
              <Label>Category *</Label>
              <Select value={form.category} onValueChange={(v) => set('category', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>{c.replace(/_/g, ' ')}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Condition</Label>
              <Select value={form.condition as string} onValueChange={(v) => set('condition', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CONDITIONS.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Brand</Label>
              <Input
                value={form.brand ?? ''}
                onChange={(e) => set('brand', e.target.value || null)}
                placeholder="Apple, Dell, HP…"
              />
            </div>
            <div className="space-y-1">
              <Label>Serial Number</Label>
              <Input
                value={form.serial_number ?? ''}
                onChange={(e) => set('serial_number', e.target.value || null)}
              />
            </div>
            <div className="space-y-1">
              <Label>Purchase Cost (PKR)</Label>
              <Input
                type="number"
                min={0}
                value={form.purchase_cost ?? ''}
                onChange={(e) => set('purchase_cost', e.target.value ? Number(e.target.value) : null)}
              />
            </div>
            <div className="space-y-1">
              <Label>Warranty Expiry</Label>
              <Input
                type="date"
                value={form.warranty_expiry ?? ''}
                onChange={(e) => set('warranty_expiry', e.target.value || null)}
              />
            </div>
            <div className="col-span-2 space-y-1">
              <Label>Location / Storage</Label>
              <Input
                value={form.location ?? ''}
                onChange={(e) => set('location', e.target.value || null)}
                placeholder="e.g. IT Room Cabinet A"
              />
            </div>
            <div className="col-span-2 space-y-1">
              <Label>Notes</Label>
              <Textarea
                rows={2}
                value={form.notes ?? ''}
                onChange={(e) => set('notes', e.target.value || null)}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving…' : isEdit ? 'Save Changes' : 'Add Asset'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Assign Dialog ────────────────────────────────────────────────────────────

function AssignDialog({ assetId, onClose }: { assetId: string; onClose: () => void }) {
  const assignAsset = useAssignAsset();
  const [employeeId, setEmployeeId] = useState('');
  const [condition, setCondition]   = useState<AssetCondition>('good');
  const [notes, setNotes]           = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await assignAsset.mutateAsync({
      id: assetId,
      data: { employee_id: employeeId, condition_at_assignment: condition, notes: notes || null },
    });
    onClose();
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>Assign Asset</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1">
            <Label>Employee ID *</Label>
            <Input
              required
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              placeholder="Paste employee UUID"
            />
          </div>
          <div className="space-y-1">
            <Label>Condition at Assignment</Label>
            <Select value={condition} onValueChange={(v) => setCondition(v as AssetCondition)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {CONDITIONS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Notes</Label>
            <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={assignAsset.isPending}>
              {assignAsset.isPending ? 'Assigning…' : 'Assign'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Return Dialog ────────────────────────────────────────────────────────────

function ReturnDialog({ assetId, onClose }: { assetId: string; onClose: () => void }) {
  const returnAsset = useReturnAsset();
  const [condition, setCondition]     = useState<AssetCondition>('good');
  const [notes, setNotes]             = useState('');
  const [isDamaged, setIsDamaged]     = useState(false);
  const [damageDesc, setDamageDesc]   = useState('');
  const [damageCost, setDamageCost]   = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await returnAsset.mutateAsync({
      id: assetId,
      data: {
        condition_at_return: condition,
        notes:               notes || null,
        is_damaged:          isDamaged,
        damage_description:  isDamaged ? damageDesc : null,
        damage_cost:         isDamaged && damageCost ? Number(damageCost) : null,
      },
    });
    onClose();
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>Return Asset</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1">
            <Label>Condition at Return</Label>
            <Select value={condition} onValueChange={(v) => setCondition(v as AssetCondition)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {CONDITIONS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Return Notes</Label>
            <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isDamaged}
              onChange={(e) => setIsDamaged(e.target.checked)}
            />
            <span className="text-sm text-red-600 font-medium">Asset is damaged</span>
          </label>
          {isDamaged && (
            <>
              <div className="space-y-1">
                <Label>Damage Description</Label>
                <Textarea rows={2} value={damageDesc} onChange={(e) => setDamageDesc(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>Damage Cost (PKR)</Label>
                <Input
                  type="number"
                  min={0}
                  value={damageCost}
                  onChange={(e) => setDamageCost(e.target.value)}
                />
              </div>
            </>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={returnAsset.isPending}>
              {returnAsset.isPending ? 'Processing…' : 'Confirm Return'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Asset History Dialog ─────────────────────────────────────────────────────

function HistoryDialog({ assetId, assetName, onClose }: {
  assetId: string; assetName: string; onClose: () => void;
}) {
  const { data: history = [], isLoading } = useAssetHistory(assetId);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Assignment History — {assetName}</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="py-8 text-center text-slate-400">Loading…</div>
        ) : history.length === 0 ? (
          <div className="py-8 text-center text-slate-400">No assignment history.</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Employee</TableHead>
                <TableHead>Assigned</TableHead>
                <TableHead>Returned</TableHead>
                <TableHead>Condition In</TableHead>
                <TableHead>Condition Out</TableHead>
                <TableHead>Damaged</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.map((h) => (
                <TableRow key={h.id}>
                  <TableCell className="text-sm font-medium">
                    {h.employee?.full_name ?? h.employee_id}
                  </TableCell>
                  <TableCell className="text-sm">{h.assigned_at}</TableCell>
                  <TableCell className="text-sm">{h.returned_at ?? <span className="text-blue-600">Active</span>}</TableCell>
                  <TableCell>
                    <span className={`text-xs capitalize ${CONDITION_COLORS[h.condition_at_assignment as AssetCondition]}`}>
                      {h.condition_at_assignment}
                    </span>
                  </TableCell>
                  <TableCell>
                    {h.condition_at_return
                      ? <span className={`text-xs capitalize ${CONDITION_COLORS[h.condition_at_return as AssetCondition]}`}>{h.condition_at_return}</span>
                      : <span className="text-slate-300 text-xs">—</span>
                    }
                  </TableCell>
                  <TableCell>
                    {h.is_damaged
                      ? <Badge variant="outline" className="bg-red-50 text-red-600 border-red-200 text-xs">Damaged</Badge>
                      : <span className="text-slate-300 text-xs">—</span>
                    }
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── Warranty cell — client-only to avoid SSR/hydration date mismatch ────────

function WarrantyCell({ expiry }: { expiry: string | null | undefined }) {
  const [expired, setExpired] = useState<boolean | null>(null);
  useEffect(() => {
    setExpired(!!expiry && new Date(expiry) < new Date());
  }, [expiry]);

  if (!expiry) return <span>—</span>;
  if (expired === null) return <span className="text-slate-400">{expiry}</span>;
  return expired
    ? <span className="text-red-500">Expired</span>
    : <span>{expiry}</span>;
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AssetsPage() {
  const [search, setSearch]             = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate]     = useState(false);
  const [editAsset, setEditAsset]       = useState<AssetListItem | null>(null);
  const [assignId, setAssignId]         = useState<string | null>(null);
  const [returnId, setReturnId]         = useState<string | null>(null);
  const [historyAsset, setHistoryAsset] = useState<AssetListItem | null>(null);

  const filters: Partial<AssetFilterParams> = {
    search:   search    || undefined,
    category: (categoryFilter as AssetCategory) || undefined,
    status:   (statusFilter   as AssetStatus)   || undefined,
  };

  const { data, isLoading, refetch } = useAssets(filters);
  const assets = data?.results ?? [];

  // Stats from full unfiltered count (quick approximation)
  const { data: allData } = useAssets({});
  const allAssets = allData?.results ?? [];
  const stats = {
    total:       allData?.count   ?? 0,
    assigned:    allAssets.filter((a) => a.status === 'assigned').length,
    available:   allAssets.filter((a) => a.status === 'available').length,
    maintenance: allAssets.filter((a) => a.status === 'maintenance').length,
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Monitor className="h-6 w-6 text-blue-600" />
            Asset Management
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            IT equipment, furniture, vehicles &amp; inventory
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Add Asset
          </Button>
        </div>
      </div>

      {/* Stats */}
      <AssetStats {...stats} />

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            className="pl-8"
            placeholder="Search by name, tag, serial…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={categoryFilter || 'all'} onValueChange={(v) => setCategoryFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>{c.replace(/_/g,' ')}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter || 'all'} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="available">Available</SelectItem>
            <SelectItem value="assigned">Assigned</SelectItem>
            <SelectItem value="maintenance">Maintenance</SelectItem>
            <SelectItem value="retired">Retired</SelectItem>
            <SelectItem value="lost">Lost</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="py-12 text-center text-slate-400">Loading…</div>
      ) : assets.length === 0 ? (
        <div className="py-16 text-center text-slate-400">
          <Monitor className="h-12 w-12 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No assets found</p>
          <p className="text-sm">Add your first asset to get started</p>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tag</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Brand</TableHead>
                <TableHead>Assigned To</TableHead>
                <TableHead>Condition</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Warranty</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {assets.map((a) => (
                <TableRow key={a.id} className="hover:bg-slate-50">
                  <TableCell className="font-mono text-xs text-slate-500">{a.asset_tag}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">
                        {CATEGORY_ICONS[a.category] ?? <Package className="h-4 w-4" />}
                      </span>
                      <span className="font-medium text-sm">{a.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm capitalize">{a.category.replace(/_/g,' ')}</TableCell>
                  <TableCell className="text-sm text-slate-500">{a.brand ?? '—'}</TableCell>
                  <TableCell className="text-sm">
                    {a.current_employee
                      ? <div>
                          <p className="font-medium">{a.current_employee.full_name}</p>
                          {a.assigned_since && (
                            <p className="text-xs text-slate-400">since {a.assigned_since}</p>
                          )}
                        </div>
                      : <span className="text-slate-300">—</span>
                    }
                  </TableCell>
                  <TableCell>
                    <span className={`text-xs capitalize ${CONDITION_COLORS[a.condition as AssetCondition]}`}>
                      {a.condition}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={`text-xs ${STATUS_COLORS[a.status as AssetStatus]}`}>
                      {a.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-slate-500">
                    <WarrantyCell expiry={a.warranty_expiry} />
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {a.status === 'available' && (
                          <DropdownMenuItem onClick={() => setAssignId(a.id)}>
                            <UserCheck className="h-4 w-4 mr-2 text-blue-600" />
                            Assign
                          </DropdownMenuItem>
                        )}
                        {a.status === 'assigned' && (
                          <DropdownMenuItem onClick={() => setReturnId(a.id)}>
                            <RotateCcw className="h-4 w-4 mr-2 text-green-600" />
                            Return
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem onClick={() => setEditAsset(a)}>
                          Edit Details
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setHistoryAsset(a)}>
                          View History
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {data && (
        <p className="text-xs text-slate-400 text-center">
          Showing {assets.length} of {data.count} assets
        </p>
      )}

      {/* Dialogs */}
      <AssetFormDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
      />
      {editAsset && (
        <AssetFormDialog
          open
          initial={editAsset}
          onClose={() => setEditAsset(null)}
        />
      )}
      {assignId && (
        <AssignDialog assetId={assignId} onClose={() => setAssignId(null)} />
      )}
      {returnId && (
        <ReturnDialog assetId={returnId} onClose={() => setReturnId(null)} />
      )}
      {historyAsset && (
        <HistoryDialog
          assetId={historyAsset.id}
          assetName={historyAsset.name}
          onClose={() => setHistoryAsset(null)}
        />
      )}
    </div>
  );
}
