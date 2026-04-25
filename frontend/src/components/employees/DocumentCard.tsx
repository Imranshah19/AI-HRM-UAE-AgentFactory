'use client';

import { useState } from 'react';
import {
  FileText, FileImage, File, Download, Trash2,
  AlertTriangle, Clock, CheckCircle,
} from 'lucide-react';
import { format, differenceInDays, isPast } from 'date-fns';

import { Button }  from '@/components/ui/button';
import { Badge }   from '@/components/ui/badge';
import { cn }      from '@/lib/utils';
import type { EmployeeDocument } from '@/types/employee';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const DOC_TYPE_LABELS: Record<string, string> = {
  cnic:              'CNIC',
  passport:          'Passport',
  degree:            'Degree',
  experience_letter: 'Experience Letter',
  offer_letter:      'Offer Letter',
  contract:          'Contract',
  nda:               'NDA',
  medical:           'Medical Certificate',
  other:             'Other',
};

function DocIcon({ mimeType }: { mimeType: string | null }) {
  if (!mimeType) return <File className="h-8 w-8 text-slate-400" />;
  if (mimeType.startsWith('image/'))       return <FileImage className="h-8 w-8 text-blue-500" />;
  if (mimeType === 'application/pdf')      return <FileText  className="h-8 w-8 text-red-500"  />;
  return <File className="h-8 w-8 text-slate-400" />;
}

type ExpiryState = 'expired' | 'warning' | 'ok' | 'none';

function getExpiryState(expiresAt: string | null | undefined): ExpiryState {
  if (!expiresAt) return 'none';
  const date = new Date(expiresAt);
  if (isPast(date)) return 'expired';
  if (differenceInDays(date, new Date()) <= 30) return 'warning';
  return 'ok';
}

// ─── Component ────────────────────────────────────────────────────────────────

interface DocumentCardProps {
  document:    EmployeeDocument;
  onDownload?: (doc: EmployeeDocument) => void;
  onDelete?:   (docId: string) => void;
  isDeleting?: boolean;
  canDelete?:  boolean;
}

export function DocumentCard({
  document: doc,
  onDownload,
  onDelete,
  isDeleting = false,
  canDelete  = false,
}: DocumentCardProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  const expiryState = getExpiryState(doc.expires_at);
  const label       = DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type;

  function handleDelete() {
    if (!confirmDelete) { setConfirmDelete(true); return; }
    onDelete?.(doc.id);
    setConfirmDelete(false);
  }

  return (
    <div
      className={cn(
        'relative flex items-start gap-3 p-4 rounded-lg border bg-white dark:bg-slate-900 transition-shadow hover:shadow-sm',
        expiryState === 'expired' && 'border-red-300 bg-red-50/30 dark:bg-red-950/10',
        expiryState === 'warning' && 'border-yellow-300 bg-yellow-50/30 dark:bg-yellow-950/10',
      )}
    >
      {/* Icon */}
      <div className="shrink-0 mt-0.5">
        <DocIcon mimeType={doc.mime_type} />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        {/* Type + status row */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
            {label}
          </span>
          {expiryState === 'expired' && (
            <Badge variant="destructive" className="text-[10px] px-1.5 py-0">Expired</Badge>
          )}
          {expiryState === 'warning' && (
            <Badge className="text-[10px] px-1.5 py-0 bg-yellow-100 text-yellow-800 border-yellow-300">
              Expiring soon
            </Badge>
          )}
          {expiryState === 'ok' && (
            <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
          )}
        </div>

        {/* File name */}
        {doc.file_name && (
          <p className="text-xs text-slate-500 truncate mt-0.5">{doc.file_name}</p>
        )}

        {/* Dates */}
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5">
          <span className="text-[11px] text-slate-400 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Uploaded {doc.uploaded_at ? format(new Date(doc.uploaded_at), 'dd MMM yyyy') : '—'}
          </span>
          {doc.expires_at && (
            <span
              className={cn(
                'text-[11px] flex items-center gap-1',
                expiryState === 'expired' ? 'text-red-600 font-medium' :
                expiryState === 'warning' ? 'text-yellow-700 font-medium' :
                'text-slate-400',
              )}
            >
              <AlertTriangle className="h-3 w-3" />
              Expires {doc.expires_at ? format(new Date(doc.expires_at), 'dd MMM yyyy') : '—'}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        {onDownload && (
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7"
            onClick={() => onDownload(doc)}
            title="Download"
          >
            <Download className="h-3.5 w-3.5" />
          </Button>
        )}
        {canDelete && onDelete && (
          <Button
            size="icon"
            variant={confirmDelete ? 'destructive' : 'ghost'}
            className="h-7 w-7"
            onClick={handleDelete}
            disabled={isDeleting}
            title={confirmDelete ? 'Click again to confirm' : 'Delete'}
            onBlur={() => setConfirmDelete(false)}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}
