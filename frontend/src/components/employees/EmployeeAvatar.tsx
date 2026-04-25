import { getInitials } from '@/lib/utils';
import { cn }          from '@/lib/utils';

// ─── Size map ─────────────────────────────────────────────────────────────────

const SIZE: Record<string, string> = {
  xs:  'w-6 h-6 text-[10px]',
  sm:  'w-8 h-8 text-xs',
  md:  'w-10 h-10 text-sm',
  lg:  'w-12 h-12 text-base',
  xl:  'w-20 h-20 text-xl',
  '2xl': 'w-28 h-28 text-2xl',
};

// A deterministic colour from the name so every person has a consistent avatar
const PALETTE = [
  'bg-blue-100 text-blue-700',
  'bg-violet-100 text-violet-700',
  'bg-emerald-100 text-emerald-700',
  'bg-amber-100 text-amber-700',
  'bg-rose-100 text-rose-700',
  'bg-cyan-100 text-cyan-700',
  'bg-fuchsia-100 text-fuchsia-700',
  'bg-orange-100 text-orange-700',
];

function colorForName(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash += name.charCodeAt(i);
  return PALETTE[hash % PALETTE.length];
}

// ─── Component ────────────────────────────────────────────────────────────────

interface EmployeeAvatarProps {
  name:              string;
  photoUrl?:         string | null;
  size?:             keyof typeof SIZE;
  online?:           boolean;
  className?:        string;
}

export function EmployeeAvatar({
  name,
  photoUrl,
  size = 'md',
  online,
  className,
}: EmployeeAvatarProps) {
  const sizeClass   = SIZE[size] ?? SIZE.md;
  const colorClass  = colorForName(name);
  const initials    = getInitials(name);

  return (
    <div className={cn('relative shrink-0', className)}>
      {photoUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={photoUrl}
          alt={name}
          className={cn('rounded-full object-cover', sizeClass)}
        />
      ) : (
        <div
          className={cn(
            'rounded-full flex items-center justify-center font-semibold select-none',
            sizeClass,
            colorClass,
          )}
          aria-label={name}
        >
          {initials}
        </div>
      )}

      {online !== undefined && (
        <span
          className={cn(
            'absolute bottom-0 right-0 rounded-full border-2 border-white',
            size === 'xs' || size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5',
            online ? 'bg-green-500' : 'bg-slate-300',
          )}
          aria-label={online ? 'Online' : 'Offline'}
        />
      )}
    </div>
  );
}
