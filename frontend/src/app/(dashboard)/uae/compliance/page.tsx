"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function UAECompliancePage() {
  const [lang, setLang] = useState<"en" | "ar">("en");
  const [darkMode, setDarkMode] = useState(false);
  const isAr = lang === "ar";
  const dir = isAr ? "rtl" : "ltr";

  const today = new Date();
  const toDate = (s: string) => new Date(s);
  const daysUntil = (s: string) => Math.floor((toDate(s).getTime() - today.getTime()) / 86400000);

  const wpsData = [
    { company: "Company A", name_ar: "الشركة أ", status: "submitted", due: "2026-04-28", submitted: "2026-04-20", amount: "432,750" },
    { company: "Company B", name_ar: "الشركة ب", status: "pending",   due: "2026-04-28", submitted: null, amount: "1,417,250" },
  ];

  const emiratisationData = [
    { company: "Company A", name_ar: "الشركة أ", total: 55, emiratis: 2, pct: "3.64", required: "4.00", gap: 1, fine: "7,000" },
    { company: "Company B", name_ar: "الشركة ب", total: 120, emiratis: 4, pct: "3.33", required: "4.00", gap: 1, fine: "7,000" },
  ];

  const expiringDocs = [
    { employee: "Ahmed Al-Rashidi", emp_ar: "أحمد الراشدي", type: "Passport", type_ar: "جواز السفر", expiry: "2026-05-19", company: "Company A" },
    { employee: "Priya Sharma", emp_ar: "بريا شارما", type: "Emirates ID", type_ar: "الهوية الإماراتية", expiry: "2026-05-07", company: "Company A" },
    { employee: "Juan Santos", emp_ar: "خوان سانتوس", type: "Visa", type_ar: "تأشيرة", expiry: "2026-04-29", company: "Company B" },
  ];

  const expiringContracts = [
    { employee: "Maria Reyes", emp_ar: "ماريا رييس", expiry: "2026-05-15", service_years: "2.1", notice: "30 days", company: "Company A" },
    { employee: "Rajiv Kumar", emp_ar: "راجيف كومار", expiry: "2026-07-10", service_years: "3.5", notice: "30 days", company: "Company B" },
  ];

  return (
    <div className={`min-h-screen p-6 ${darkMode ? "bg-gray-900 text-white" : "bg-gray-50"}`} dir={dir}>

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {isAr ? "الامتثال القانوني — الإمارات" : "UAE Compliance Center"}
          </h1>
          <p className="text-sm text-gray-500">
            {isAr ? "WPS • التوطين • الوثائق • العقود • التأمين" : "WPS • Emiratisation • Documents • Contracts • Insurance"}
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

      <Tabs defaultValue="wps">
        <TabsList className="mb-6">
          <TabsTrigger value="wps">🏦 {isAr ? "WPS" : "WPS"}</TabsTrigger>
          <TabsTrigger value="emiratisation">🇦🇪 {isAr ? "التوطين" : "Emiratisation"}</TabsTrigger>
          <TabsTrigger value="documents">📄 {isAr ? "الوثائق" : "Documents"}</TabsTrigger>
          <TabsTrigger value="contracts">📋 {isAr ? "العقود والتأمين" : "Contracts & Insurance"}</TabsTrigger>
        </TabsList>

        {/* ── WPS Tab ────────────────────────────────────────────────────────── */}
        <TabsContent value="wps">
          <div className={`rounded-lg border overflow-hidden ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
            <div className="p-4 border-b">
              <h2 className="font-semibold">{isAr ? "حالة تقديم WPS" : "WPS Submission Status — All Companies"}</h2>
            </div>
            <table className="w-full text-sm">
              <thead className={darkMode ? "bg-gray-700" : "bg-gray-50"}>
                <tr>
                  <th className="text-left px-4 py-3">{isAr ? "الشركة" : "Company"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "الحالة" : "Status"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "تاريخ الاستحقاق" : "Due Date"}</th>
                  <th className="text-right px-4 py-3">{isAr ? "المبلغ (درهم)" : "Amount (AED)"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "إجراء" : "Action"}</th>
                </tr>
              </thead>
              <tbody>
                {wpsData.map((w) => (
                  <tr key={w.company} className={`border-t ${darkMode ? "border-gray-700" : "border-gray-100"}`}>
                    <td className="px-4 py-3 font-medium">{isAr ? w.name_ar : w.company}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        w.status === "submitted"
                          ? "bg-green-100 text-green-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {w.status === "submitted" ? (isAr ? "✅ مُقدَّم" : "✅ Submitted") : (isAr ? "⏳ معلق" : "⏳ Pending")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-500">{w.due}</td>
                    <td className="px-4 py-3 text-right font-semibold">AED {w.amount}</td>
                    <td className="px-4 py-3 text-center">
                      {w.status === "pending" && (
                        <Button size="sm" className="bg-blue-600 text-white text-xs">
                          {isAr ? "توليد ملف SIF" : "Generate SIF"}
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 p-3 bg-orange-50 rounded text-xs text-orange-700">
            {isAr
              ? "تحذير: WPS يجب تقديمه بحلول نهاية الشهر. التأخر لأكثر من 17 يوماً يخاطر بتعليق تصاريح العمل."
              : "Warning: WPS must be submitted by end of month. 17+ days late risks work permit suspension."}
          </div>
        </TabsContent>

        {/* ── Emiratisation Tab ─────────────────────────────────────────────── */}
        <TabsContent value="emiratisation">
          <div className={`rounded-lg border overflow-hidden ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
            <table className="w-full text-sm">
              <thead className={darkMode ? "bg-gray-700" : "bg-gray-50"}>
                <tr>
                  <th className="text-left px-4 py-3">{isAr ? "الشركة" : "Company"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "إجمالي الموظفين" : "Total"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "الإماراتيون" : "Emiratis"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "النسبة الحالية" : "Current %"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "المطلوب" : "Required %"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "الفجوة" : "Gap"}</th>
                  <th className="text-right px-4 py-3">{isAr ? "مخاطر الغرامة (سنوي)" : "Annual Fine Risk (AED)"}</th>
                </tr>
              </thead>
              <tbody>
                {emiratisationData.map((e) => (
                  <tr key={e.company} className={`border-t ${darkMode ? "border-gray-700" : ""}`}>
                    <td className="px-4 py-3 font-medium">{isAr ? e.name_ar : e.company}</td>
                    <td className="px-4 py-3 text-center">{e.total}</td>
                    <td className="px-4 py-3 text-center text-green-600 font-semibold">{e.emiratis}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-red-600 font-bold">{e.pct}%</span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-500">{e.required}%</td>
                    <td className="px-4 py-3 text-center">
                      <span className="bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded">
                        -{e.gap} {isAr ? "موظف" : "short"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-red-600 font-bold">AED {e.fine}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 p-3 bg-red-50 rounded text-xs text-red-700">
            {isAr
              ? "غرامة عدم الامتثال: AED 6,000-7,000 لكل موظف إماراتي ناقص سنوياً (قرار وزارة الموارد البشرية 2024)"
              : "Non-compliance fine: AED 6,000-7,000 per missing Emirati per year (MOHRE 2024 regulations)"}
          </div>
        </TabsContent>

        {/* ── Documents Tab ─────────────────────────────────────────────────── */}
        <TabsContent value="documents">
          <div className={`rounded-lg border overflow-hidden ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="font-semibold">{isAr ? "الوثائق المنتهية قريباً" : "Expiring Documents — Next 90 Days"}</h2>
              <Button size="sm" variant="outline">{isAr ? "تصدير" : "Export"}</Button>
            </div>
            <table className="w-full text-sm">
              <thead className={darkMode ? "bg-gray-700" : "bg-gray-50"}>
                <tr>
                  <th className="text-left px-4 py-3">{isAr ? "الموظف" : "Employee"}</th>
                  <th className="text-left px-4 py-3">{isAr ? "نوع الوثيقة" : "Document"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "تاريخ الانتهاء" : "Expiry"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "الأيام المتبقية" : "Days Left"}</th>
                  <th className="text-center px-4 py-3">{isAr ? "الحالة" : "Status"}</th>
                  <th className="text-left px-4 py-3">{isAr ? "الشركة" : "Company"}</th>
                </tr>
              </thead>
              <tbody>
                {expiringDocs.map((doc, idx) => {
                  const days = daysUntil(doc.expiry);
                  return (
                    <tr key={idx} className={`border-t ${darkMode ? "border-gray-700" : ""}`}>
                      <td className="px-4 py-3 font-medium">{isAr ? doc.emp_ar : doc.employee}</td>
                      <td className="px-4 py-3">{isAr ? doc.type_ar : doc.type}</td>
                      <td className="px-4 py-3 text-center text-gray-500">{doc.expiry}</td>
                      <td className="px-4 py-3 text-center font-bold" style={{ color: days <= 14 ? "#dc2626" : days <= 30 ? "#d97706" : "#374151" }}>
                        {days}d
                      </td>
                      <td className="px-4 py-3 text-center">
                        {days <= 0 ? <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">🔴 Expired</span>
                         : days <= 14 ? <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">🔴 Critical</span>
                         : days <= 30 ? <span className="text-xs bg-orange-100 text-orange-800 px-2 py-0.5 rounded">🟡 Urgent</span>
                         : <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">🟡 Soon</span>
                        }
                      </td>
                      <td className="px-4 py-3 text-gray-500">{doc.company}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </TabsContent>

        {/* ── Contracts + Insurance Tab ──────────────────────────────────────── */}
        <TabsContent value="contracts">
          <div className="space-y-4">
            <div className={`rounded-lg border overflow-hidden ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
              <div className="p-4 border-b">
                <h2 className="font-semibold">{isAr ? "العقود المنتهية" : "Expiring Contracts"}</h2>
              </div>
              <table className="w-full text-sm">
                <thead className={darkMode ? "bg-gray-700" : "bg-gray-50"}>
                  <tr>
                    <th className="text-left px-4 py-3">{isAr ? "الموظف" : "Employee"}</th>
                    <th className="text-center px-4 py-3">{isAr ? "انتهاء العقد" : "Contract End"}</th>
                    <th className="text-center px-4 py-3">{isAr ? "سنوات الخدمة" : "Service Years"}</th>
                    <th className="text-center px-4 py-3">{isAr ? "فترة الإشعار" : "Notice Period"}</th>
                    <th className="text-center px-4 py-3">{isAr ? "إجراء" : "Action"}</th>
                  </tr>
                </thead>
                <tbody>
                  {expiringContracts.map((c, idx) => (
                    <tr key={idx} className={`border-t ${darkMode ? "border-gray-700" : ""}`}>
                      <td className="px-4 py-3 font-medium">{isAr ? c.emp_ar : c.employee}</td>
                      <td className="px-4 py-3 text-center text-orange-600">{c.expiry}</td>
                      <td className="px-4 py-3 text-center">{c.service_years}y</td>
                      <td className="px-4 py-3 text-center">{c.notice}</td>
                      <td className="px-4 py-3 text-center">
                        <Button size="sm" variant="outline" className="text-xs">
                          {isAr ? "تجديد" : "Renew"}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="p-3 bg-blue-50 rounded text-xs text-blue-700">
              {isAr
                ? "قانون الإمارات: جميع العقود يجب أن تكون محددة المدة (تم إلغاء العقود غير المحددة في فبراير 2022). الحد الأقصى 3 سنوات قابلة للتجديد."
                : "UAE Law: All contracts must be fixed-term (unlimited contracts abolished Feb 2022). Maximum 3 years, renewable."}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
