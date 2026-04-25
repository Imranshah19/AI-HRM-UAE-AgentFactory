"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CompanyCard {
  id: string;
  name_en: string;
  name_ar: string;
  emirate: string;
  employee_count: number;
  wps_status: "submitted" | "pending" | "overdue";
  emiratisation_pct: string;
  emiratisation_compliant: boolean;
  alerts: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const WPS_STATUS_CONFIG = {
  submitted: { label: "WPS Submitted", labelAr: "تم تقديم الرواتب", color: "bg-green-100 text-green-800" },
  pending:   { label: "WPS Pending",   labelAr: "في الانتظار",       color: "bg-yellow-100 text-yellow-800" },
  overdue:   { label: "WPS Overdue",   labelAr: "متأخر",             color: "bg-red-100 text-red-800" },
};

const MOCK_COMPANIES: CompanyCard[] = [
  { id: "co-001", name_en: "Gulf Holdings — Company A", name_ar: "خليج هولدينج — الشركة أ",
    emirate: "Dubai", employee_count: 55, wps_status: "submitted",
    emiratisation_pct: "3.64", emiratisation_compliant: false, alerts: 3 },
  { id: "co-002", name_en: "Gulf Holdings — Company B", name_ar: "خليج هولدينج — الشركة ب",
    emirate: "Abu Dhabi", employee_count: 120, wps_status: "submitted",
    emiratisation_pct: "3.33", emiratisation_compliant: false, alerts: 4 },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function UAEGroupDashboardPage() {
  const [lang, setLang] = useState<"en" | "ar">("en");
  const [darkMode, setDarkMode] = useState(false);
  const isAr = lang === "ar";
  const dir = isAr ? "rtl" : "ltr";

  const todayGregorian = new Date().toLocaleDateString("en-AE", {
    day: "2-digit", month: "short", year: "numeric",
  });

  return (
    <div className={`min-h-screen p-6 ${darkMode ? "bg-gray-900 text-white" : "bg-gray-50 text-gray-900"}`} dir={dir}>

      {/* ── Top bar ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {isAr ? "لوحة تحكم المجموعة — الإمارات" : "Group Dashboard — UAE AI-HRM"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{todayGregorian}</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setLang(isAr ? "en" : "ar")}
          >
            {isAr ? "EN" : "عربي"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDarkMode(!darkMode)}
          >
            {darkMode ? "☀️" : "🌙"}
          </Button>
        </div>
      </div>

      {/* ── Group stats row ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label={isAr ? "إجمالي الموظفين" : "Total Employees"}
          value="175"
          color="blue"
        />
        <StatCard
          label={isAr ? "إجمالي الرواتب الشهرية" : "Monthly Payroll"}
          value="AED 1.85M"
          color="green"
        />
        <StatCard
          label={isAr ? "التنبيهات الحرجة" : "Critical Alerts"}
          value="7"
          color="red"
        />
        <StatCard
          label={isAr ? "متوسط نسبة التوطين" : "Avg Emiratisation"}
          value="3.2%"
          color="yellow"
          note={isAr ? "الهدف: 4%" : "Target: 4%"}
        />
      </div>

      {/* ── Company cards grid ───────────────────────────────────────────────── */}
      <h2 className="text-lg font-semibold mb-3">
        {isAr ? "الشركات" : "Companies"}
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {MOCK_COMPANIES.map((company) => (
          <CompanyCardWidget key={company.id} company={company} lang={lang} darkMode={darkMode} />
        ))}
      </div>

      {/* ── Critical alerts panel ────────────────────────────────────────────── */}
      <div className={`rounded-lg border p-4 mb-6 ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
        <h2 className="text-lg font-semibold mb-3 text-red-600">
          {isAr ? "⚠️ التنبيهات الحرجة" : "⚠️ Critical Alerts — Group Level"}
        </h2>
        <div className="space-y-2">
          <AlertRow
            icon="🔴"
            message={isAr ? "3 موظفين تأشيراتهم ستنتهي خلال 14 يوماً" : "3 employees with visas expiring in 14 days"}
            company="Company A"
            level="critical"
          />
          <AlertRow
            icon="🔴"
            message={isAr ? "شركتان دون نسبة التوطين المطلوبة (4%)" : "2 companies below Emiratisation target (4%)"}
            company="All"
            level="critical"
          />
          <AlertRow
            icon="🟡"
            message={isAr ? "5 بوالص تأمين تنتهي خلال 30 يوماً" : "5 insurance policies expiring in 30 days"}
            company="Company B"
            level="urgent"
          />
          <AlertRow
            icon="🟡"
            message={isAr ? "4 عقود تنتهي خلال 90 يوماً" : "4 contracts expiring in 90 days"}
            company="Company B"
            level="urgent"
          />
        </div>
      </div>

      {/* ── Agent status mini-widget ─────────────────────────────────────────── */}
      <div className={`rounded-lg border p-4 ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
        <h2 className="text-lg font-semibold mb-3">
          {isAr ? "حالة الوكلاء الذكيين (15 وكيل)" : "AI Agents Status (15 Agents)"}
        </h2>
        <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
          {AGENT_NAMES.map((agent) => (
            <div key={agent.key} className={`rounded px-2 py-1 text-xs text-center ${
              darkMode ? "bg-gray-700" : "bg-gray-100"
            }`}>
              <span className="text-green-500">●</span>{" "}
              <span className="font-medium">{isAr ? agent.ar : agent.en}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {isAr ? "وضع: تجريبي (لا مفتاح API)" : "Mode: Mock (no ANTHROPIC_API_KEY) — Set key for live AI"}
        </p>
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({ label, value, color, note }: {
  label: string; value: string; color: string; note?: string;
}) {
  const colorMap: Record<string, string> = {
    blue: "border-l-4 border-blue-500",
    green: "border-l-4 border-green-500",
    red: "border-l-4 border-red-500",
    yellow: "border-l-4 border-yellow-500",
  };
  return (
    <div className={`bg-white rounded-lg p-4 shadow-sm ${colorMap[color]}`}>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {note && <p className="text-xs text-gray-400 mt-1">{note}</p>}
    </div>
  );
}

function CompanyCardWidget({ company, lang, darkMode }: {
  company: CompanyCard; lang: "en" | "ar"; darkMode: boolean;
}) {
  const isAr = lang === "ar";
  const wpsConfig = WPS_STATUS_CONFIG[company.wps_status];
  return (
    <div
      className={`rounded-lg border p-4 cursor-pointer hover:shadow-md transition-shadow ${
        darkMode ? "bg-gray-800 border-gray-700" : "bg-white"
      }`}
      onClick={() => window.location.href = `/uae/company/${company.id}/dashboard`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold">{isAr ? company.name_ar : company.name_en}</h3>
          <p className="text-xs text-gray-500">{company.emirate}</p>
        </div>
        {company.alerts > 0 && (
          <span className="bg-red-100 text-red-800 text-xs font-bold px-2 py-1 rounded-full">
            {company.alerts} {isAr ? "تنبيه" : "alerts"}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
          {company.employee_count} {isAr ? "موظف" : "employees"}
        </span>
        <span className={`text-xs px-2 py-1 rounded ${wpsConfig.color}`}>
          {isAr ? wpsConfig.labelAr : wpsConfig.label}
        </span>
        <span className={`text-xs px-2 py-1 rounded ${
          company.emiratisation_compliant
            ? "bg-green-100 text-green-800"
            : "bg-red-100 text-red-800"
        }`}>
          {isAr ? "التوطين" : "Emiratisation"}: {company.emiratisation_pct}%
        </span>
      </div>
    </div>
  );
}

function AlertRow({ icon, message, company, level }: {
  icon: string; message: string; company: string; level: string;
}) {
  return (
    <div className={`flex items-center gap-3 p-2 rounded text-sm ${
      level === "critical" ? "bg-red-50" : "bg-yellow-50"
    }`}>
      <span>{icon}</span>
      <span className="flex-1">{message}</span>
      <span className="text-xs text-gray-500">{company}</span>
    </div>
  );
}

const AGENT_NAMES = [
  { key: "openclaw", en: "OpenClaw", ar: "أوبن كلو" },
  { key: "paperclip", en: "Paperclip", ar: "ورقة مشبك" },
  { key: "onboarding", en: "Onboarding", ar: "التأهيل" },
  { key: "documents", en: "Documents", ar: "المستندات" },
  { key: "payroll", en: "Payroll", ar: "الرواتب" },
  { key: "wps", en: "WPS", ar: "حماية الأجور" },
  { key: "gratuity", en: "Gratuity", ar: "المكافأة" },
  { key: "leave", en: "Leave", ar: "الإجازات" },
  { key: "attendance", en: "Attendance", ar: "الحضور" },
  { key: "contract", en: "Contracts", ar: "العقود" },
  { key: "insurance", en: "Insurance", ar: "التأمين" },
  { key: "air_ticket", en: "Air Ticket", ar: "التذاكر" },
  { key: "emiratisation", en: "Emiratisation", ar: "التوطين" },
  { key: "offboarding", en: "Offboarding", ar: "إنهاء الخدمة" },
  { key: "chatbot", en: "HR Chat", ar: "الدردشة" },
];
