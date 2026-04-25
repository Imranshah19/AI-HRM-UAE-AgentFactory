'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  MessageSquare, X, Send, Trash2, Bot, User, Loader2,
  ChevronDown, Sparkles,
} from 'lucide-react';
import { nanoid } from 'nanoid';

import { Button }   from '@/components/ui/button';
import { Badge }    from '@/components/ui/badge';
import { cn }       from '@/lib/utils';

import { useChatbot, useChatSuggestions } from '@/hooks/useAI';
import type { ChatMessage, ChatResponse, SuggestedAction } from '@/types/ai';

// ─── nanoid shim if not installed ────────────────────────────────────────────
function uid() {
  return Math.random().toString(36).slice(2, 10);
}

const STORAGE_KEY = 'hrms_chat_history';

function loadHistory(): ChatMessage[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
  } catch {
    return [];
  }
}

function saveHistory(msgs: ChatMessage[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-40)));
  } catch {}
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2">
      <div className="w-7 h-7 rounded-full bg-hrms-100 flex items-center justify-center shrink-0">
        <Bot className="h-3.5 w-3.5 text-hrms-600" />
      </div>
      <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-3 py-2.5">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function LeaveBalanceCard({ data }: { data: Record<string, unknown> }) {
  const balances = (data.leave_balances as Array<{type: string; remaining: number; total: number}>) ?? [];
  return (
    <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-2">
      <p className="text-xs font-semibold text-slate-500">Leave Balance {data.year as number}</p>
      {balances.map((b) => (
        <div key={b.type} className="space-y-0.5">
          <div className="flex justify-between text-xs">
            <span className="text-slate-600">{b.type}</span>
            <span className="font-medium text-hrms-700">{b.remaining}d left</span>
          </div>
          <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-hrms-500 rounded-full"
              style={{ width: `${Math.max(5, (b.remaining / (b.total || 1)) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function PayslipCard({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1.5">
      <p className="text-xs font-semibold text-slate-500">Payslip — {data.month_label as string}</p>
      {[
        { label: 'Gross', value: data.gross_salary as number, bold: false },
        { label: 'Tax',   value: data.income_tax as number,   bold: false },
        { label: 'EOBI',  value: data.eobi_employee as number, bold: false },
        { label: 'Net',   value: data.net_salary as number,   bold: true  },
      ].map(({ label, value, bold }) => (
        <div key={label} className={cn('flex justify-between text-xs', bold && 'border-t border-slate-200 pt-1 mt-1')}>
          <span className={bold ? 'font-semibold text-slate-700' : 'text-slate-500'}>{label}</span>
          <span className={bold ? 'font-bold text-hrms-700' : 'text-slate-600'}>
            PKR {(value ?? 0).toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const router = useRouter();
  const isUser = msg.role === 'user';
  const resp   = msg.response;

  // Format bold markdown **text**
  function formatText(text: string) {
    const parts = text.split(/\*\*(.+?)\*\*/g);
    return parts.map((p, i) =>
      i % 2 === 1 ? <strong key={i}>{p}</strong> : p,
    );
  }

  return (
    <div className={cn('flex items-end gap-2', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div className={cn(
        'w-7 h-7 rounded-full flex items-center justify-center shrink-0',
        isUser ? 'bg-hrms-600' : 'bg-hrms-100',
      )}>
        {isUser
          ? <User  className="h-3.5 w-3.5 text-white" />
          : <Bot   className="h-3.5 w-3.5 text-hrms-600" />
        }
      </div>

      {/* Bubble */}
      <div className={cn(
        'max-w-[78%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
        isUser
          ? 'bg-hrms-600 text-white rounded-br-sm'
          : 'bg-white border border-slate-200 text-slate-700 rounded-bl-sm',
      )}>
        <div className="whitespace-pre-wrap">{formatText(msg.content)}</div>

        {/* Structured data cards */}
        {resp?.data && resp.intent === 'leave_balance' && (
          <LeaveBalanceCard data={resp.data as Record<string, unknown>} />
        )}
        {resp?.data && resp.intent === 'payslip' && (
          <PayslipCard data={resp.data as Record<string, unknown>} />
        )}

        {/* Attendance badge */}
        {resp?.data && resp.intent === 'attendance' && (
          <div className="mt-2">
            <Badge className="text-xs bg-slate-100 text-slate-600">
              {(resp.data.status as string) ?? '—'}
            </Badge>
          </div>
        )}

        {/* Action buttons */}
        {resp?.suggested_actions && resp.suggested_actions.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2.5">
            {resp.suggested_actions.map((action: SuggestedAction) => (
              <button
                key={action.label}
                onClick={() => router.push(action.url)}
                className="text-[11px] px-2 py-1 rounded-md bg-hrms-50 text-hrms-700 hover:bg-hrms-100 border border-hrms-200 transition-colors"
              >
                {action.label} →
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Suggestion chips ─────────────────────────────────────────────────────────

function SuggestionChips({
  suggestions,
  onSelect,
}: {
  suggestions: string[];
  onSelect: (s: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pb-2">
      {suggestions.slice(0, 4).map((s) => (
        <button
          key={s}
          onClick={() => onSelect(s)}
          className="text-[11px] px-2.5 py-1 rounded-full bg-hrms-50 text-hrms-700 hover:bg-hrms-100 border border-hrms-200 transition-colors"
        >
          {s}
        </button>
      ))}
    </div>
  );
}

// ─── Main widget ──────────────────────────────────────────────────────────────

export function ChatWidget() {
  const [open, setOpen]         = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput]       = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endRef                  = useRef<HTMLDivElement>(null);
  const inputRef                = useRef<HTMLInputElement>(null);

  const chatMutation   = useChatbot();
  const { data: suggs } = useChatSuggestions();

  // Load history from localStorage on mount
  useEffect(() => {
    const h = loadHistory();
    if (h.length > 0) setMessages(h);
  }, []);

  // Save history whenever messages change
  useEffect(() => {
    saveHistory(messages);
  }, [messages]);

  // Scroll to bottom on new message
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Focus input when chat opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 200);
    }
  }, [open]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;
    const userMsg: ChatMessage = {
      id: uid(), role: 'user', content: text.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    const history = messages.slice(-6).map((m) => ({
      role: m.role, content: m.content,
    }));

    try {
      const resp: ChatResponse = await chatMutation.mutateAsync({ message: text, history });
      const botMsg: ChatMessage = {
        id: uid(), role: 'assistant',
        content: resp.answer,
        response: resp,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setMessages((prev) => [...prev, {
        id: uid(), role: 'assistant',
        content: "Sorry, I couldn't process your request. Please try again.",
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setIsTyping(false);
    }
  }, [messages, chatMutation]);

  function clearChat() {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }

  const unreadCount = 0;  // could track new messages while closed

  return (
    <>
      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-20 right-4 z-50 w-[360px] max-w-[calc(100vw-2rem)] flex flex-col rounded-2xl shadow-2xl border border-slate-200 bg-white overflow-hidden"
             style={{ height: '520px' }}>

          {/* Header */}
          <div className="flex items-center gap-2.5 px-4 py-3 bg-hrms-600 text-white shrink-0">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold">AI HR Assistant</p>
              <p className="text-[10px] text-hrms-200">Ask about leave, payroll, policies…</p>
            </div>
            <button
              onClick={clearChat}
              className="p-1 rounded hover:bg-white/20 transition-colors"
              title="Clear chat"
            >
              <Trash2 className="h-3.5 w-3.5 opacity-80" />
            </button>
            <button
              onClick={() => setOpen(false)}
              className="p-1 rounded hover:bg-white/20 transition-colors"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 bg-slate-50">
            {messages.length === 0 && (
              <div className="text-center py-6">
                <Bot className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                <p className="text-xs text-slate-400">
                  Hi! I'm your HR assistant. Ask me about your leave, payslip, attendance, or HR policies.
                </p>
              </div>
            )}
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {isTyping && <TypingIndicator />}
            <div ref={endRef} />
          </div>

          {/* Suggestions */}
          {messages.length === 0 && suggs && suggs.suggestions.length > 0 && (
            <SuggestionChips
              suggestions={suggs.suggestions}
              onSelect={sendMessage}
            />
          )}

          {/* Input */}
          <div className="shrink-0 px-3 py-2.5 border-t border-slate-200 bg-white flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage(input);
                }
              }}
              placeholder="Ask a question…"
              disabled={isTyping}
              className="flex-1 text-sm bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 outline-none focus:border-hrms-400 focus:ring-1 focus:ring-hrms-400 disabled:opacity-50 placeholder:text-slate-400"
            />
            <Button
              size="icon"
              className="h-9 w-9 rounded-xl bg-hrms-600 hover:bg-hrms-700 shrink-0"
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isTyping}
            >
              {isTyping
                ? <Loader2 className="h-4 w-4 animate-spin" />
                : <Send className="h-4 w-4" />
              }
            </Button>
          </div>
        </div>
      )}

      {/* FAB */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'fixed bottom-4 right-4 z-50 w-14 h-14 rounded-full shadow-lg',
          'flex items-center justify-center transition-all duration-200',
          open
            ? 'bg-slate-600 hover:bg-slate-700'
            : 'bg-hrms-600 hover:bg-hrms-700',
        )}
        aria-label="Open HR Assistant"
      >
        {open
          ? <X className="h-5 w-5 text-white" />
          : (
            <>
              <MessageSquare className="h-5 w-5 text-white" />
              <span className="absolute top-0 right-0 w-3.5 h-3.5 bg-amber-400 rounded-full flex items-center justify-center">
                <Sparkles className="h-2 w-2 text-amber-900" />
              </span>
            </>
          )
        }
      </button>
    </>
  );
}
