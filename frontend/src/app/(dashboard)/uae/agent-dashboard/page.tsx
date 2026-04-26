"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const AGENTS = [
  { key: "leave",          en: "Leave",           ar: "الإجازات",           domain: "leave",          description: "9 UAE leave types — Federal Decree-Law 33/2021" },
  { key: "payroll",        en: "Payroll",         ar: "الرواتب",            domain: "payroll",        description: "AED payroll + ILOE deduction + Ramadan hours" },
  { key: "attendance",     en: "Attendance",      ar: "الحضور",             domain: "attendance",     description: "Check-in/out, Ramadan 6hr mode, anomaly detection" },
  { key: "onboarding",     en: "Onboarding",      ar: "التأهيل",            domain: "onboarding",     description: "New employee onboarding — Emirates ID, visa, WPS" },
  { key: "document",       en: "Documents",       ar: "تتبع الوثائق",      domain: "document",       description: "Passport, visa, Emirates ID expiry alerts (CRITICAL/URGENT)" },
  { key: "gratuity",       en: "Gratuity",        ar: "المكافأة",           domain: "gratuity",       description: "End-of-service gratuity — 21/30 days/year, 2yr cap" },
  { key: "wps",            en: "WPS",             ar: "حماية الأجور",       domain: "wps",            description: "MOHRE SIF XML generator + deadline + fine alerts" },
  { key: "contract",       en: "Contracts",       ar: "العقود",             domain: "contract",       description: "Limited contract expiry + notice period enforcement" },
  { key: "insurance",      en: "Insurance",       ar: "التأمين",            domain: "insurance",      description: "DHA/HAAD medical insurance + ILOE compliance" },
  { key: "air_ticket",     en: "Air Ticket",      ar: "تذاكر السفر",       domain: "air_ticket",     description: "Annual home-country air ticket entitlement (after 1yr)" },
  { key: "emiratisation",  en: "Emiratisation",   ar: "التوطين",            domain: "emiratisation",  description: "Nafis 2% quota + AED 96,000/slot fine risk" },
  { key: "offboarding",    en: "Offboarding",     ar: "إنهاء الخدمة",      domain: "offboarding",    description: "Exit settlement + 14-day payment law + visa cancel" },
  { key: "chatbot",        en: "HR Chatbot",      ar: "المساعد الذكي",     domain: "chatbot",        description: "Multilingual: EN / AR / UR / HI / TL — 5 languages" },
];

const MOCK_LOGS = [
  { time: "2026-04-25 08:04", agent: "DocumentAgentUAE", company: "Company A", action: "check_all_expiries", status: "success", duration: "234ms", mode: "mock" },
  { time: "2026-04-25 09:00", agent: "AttendanceUAEAgent", company: "All", action: "daily_report", status: "success", duration: "156ms", mode: "mock" },
  { time: "2026-04-25 09:01", agent: "OnboardingAgentUAE", company: "Company B", action: "process_new_employee", status: "success", duration: "445ms", mode: "mock" },
  { time: "2026-04-25 09:05", agent: "GratuityAgent", company: "Company A", action: "calculate", status: "success", duration: "89ms", mode: "mock" },
];

export default function UAEAgentDashboardPage() {
  const [lang, setLang] = useState<"en" | "ar">("en");
  const [darkMode, setDarkMode] = useState(false);
  const [triggerResult, setTriggerResult] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<string | null>(null);
  const isAr = lang === "ar";
  const dir = isAr ? "rtl" : "ltr";

  const handleTrigger = async (agentKey: string) => {
    setLoading(agentKey);
    await new Promise(r => setTimeout(r, 1500));
    setTriggerResult(prev => ({
      ...prev,
      [agentKey]: `[Mock] Agent "${agentKey}" executed successfully at ${new Date().toISOString()}. Set ANTHROPIC_API_KEY for live AI responses.`,
    }));
    setLoading(null);
  };

  return (
    <div className={`min-h-screen p-6 ${darkMode ? "bg-gray-900 text-white" : "bg-gray-50"}`} dir={dir}>

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {isAr ? "لوحة تحكم الوكلاء الذكيين — الإمارات" : "UAE AI Agent Dashboard"}
          </h1>
          <p className="text-sm text-gray-500">
            {isAr ? "13 وكيل ذكي — LangGraph | وضع: تجريبي (لا مفتاح API)" : "13 LangGraph Agents — claude-opus-4-7 | Mode: Mock (set ANTHROPIC_API_KEY for live)"}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setLang(isAr ? "en" : "ar")}>
            {isAr ? "EN" : "عربي"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀️" : "🌙"}
          </Button>
        </div>
      </div>

      {/* ── API mode banner ──────────────────────────────────────────────────── */}
      <div className="mb-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
        🟡 {isAr
          ? "وضع تجريبي — قم بتعيين ANTHROPIC_API_KEY في ملف .env لتفعيل الذكاء الاصطناعي الحقيقي"
          : "Mock Mode — Set ANTHROPIC_API_KEY in .env to activate live Claude AI responses. All agents work without it."}
      </div>

      <Tabs defaultValue="status">
        <TabsList className="mb-6">
          <TabsTrigger value="status">🤖 {isAr ? "حالة الوكلاء" : "Agent Status"}</TabsTrigger>
          <TabsTrigger value="logs">📋 {isAr ? "سجلات التنفيذ" : "Execution Logs"}</TabsTrigger>
          <TabsTrigger value="triggers">⚡ {isAr ? "التشغيل اليدوي" : "Manual Triggers"}</TabsTrigger>
        </TabsList>

        {/* ── Agent Status Tab ───────────────────────────────────────────────── */}
        <TabsContent value="status">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {AGENTS.map((agent) => (
              <div key={agent.key} className={`rounded-lg border p-4 ${
                darkMode ? "bg-gray-800 border-gray-700" : "bg-white"
              }`}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="font-semibold text-sm">{isAr ? agent.ar : agent.en}</p>
                    <p className="text-xs text-gray-500">{agent.domain}</p>
                  </div>
                  <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                    🟡 Mock
                  </span>
                </div>
                <p className="text-xs text-gray-500">{agent.description}</p>
                <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
                  <span>✅ {isAr ? "آخر تشغيل: قبل دقيقتين" : "Last run: 2m ago"}</span>
                  <span>·</span>
                  <span>{isAr ? "معدل النجاح: 100%" : "Success: 100%"}</span>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        {/* ── Logs Tab ───────────────────────────────────────────────────────── */}
        <TabsContent value="logs">
          <div className={`rounded-lg border overflow-hidden ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
            <table className="w-full text-sm">
              <thead className={darkMode ? "bg-gray-700" : "bg-gray-50"}>
                <tr>
                  <th className="text-left px-4 py-3">{isAr ? "الوقت" : "Time"}</th>
                  <th className="text-left px-4 py-3">{isAr ? "الوكيل" : "Agent"}</th>
                  <th className="text-left px-4 py-3">{isAr ? "الشركة" : "Company"}</th>
                  <th className="text-left px-4 py-3">{isAr ? "الإجراء" : "Action"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "الحالة" : "Status"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "المدة" : "Duration"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "الوضع" : "Mode"}</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_LOGS.map((log, idx) => (
                  <tr key={idx} className={`border-t ${darkMode ? "border-gray-700" : "border-gray-100"}`}>
                    <td className="px-4 py-2 text-xs text-gray-500">{log.time}</td>
                    <td className="px-4 py-2 font-medium text-xs">{log.agent}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">{log.company}</td>
                    <td className="px-4 py-2 text-xs">{log.action}</td>
                    <td className="px-4 py-2 text-center">
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">✅ success</span>
                    </td>
                    <td className="px-4 py-2 text-center text-xs text-gray-500">{log.duration}</td>
                    <td className="px-4 py-2 text-center">
                      <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">{log.mode}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        {/* ── Manual Triggers Tab ────────────────────────────────────────────── */}
        <TabsContent value="triggers">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { key: "documents",    label_en: "Run Document Expiry Check", label_ar: "تشغيل فحص الوثائق" },
              { key: "payroll",      label_en: "Generate Payroll (Company A)", label_ar: "إنشاء رواتب الشركة أ" },
              { key: "wps",          label_en: "Generate WPS SIF File", label_ar: "توليد ملف WPS SIF" },
              { key: "emiratisation",label_en: "Run Emiratisation Check", label_ar: "تشغيل فحص التوطين" },
              { key: "gratuity",     label_en: "Generate Gratuity Report", label_ar: "توليد تقرير المكافأة" },
              { key: "attendance",   label_en: "Generate Attendance Report", label_ar: "توليد تقرير الحضور" },
            ].map((trigger) => (
              <div key={trigger.key} className={`rounded-lg border p-4 ${
                darkMode ? "bg-gray-800 border-gray-700" : "bg-white"
              }`}>
                <div className="flex items-center justify-between mb-3">
                  <p className="font-medium text-sm">{isAr ? trigger.label_ar : trigger.label_en}</p>
                  <Button
                    size="sm"
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs"
                    onClick={() => handleTrigger(trigger.key)}
                    disabled={loading === trigger.key}
                  >
                    {loading === trigger.key
                      ? (isAr ? "جارٍ التشغيل..." : "Running...")
                      : (isAr ? "⚡ تشغيل" : "⚡ Run")}
                  </Button>
                </div>
                {triggerResult[trigger.key] && (
                  <div className="text-xs bg-green-50 text-green-700 p-2 rounded">
                    {triggerResult[trigger.key]}
                  </div>
                )}
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
