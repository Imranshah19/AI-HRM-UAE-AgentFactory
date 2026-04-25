"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function UAEPayrollPage() {
  const [lang, setLang] = useState<"en" | "ar">("en");
  const [darkMode, setDarkMode] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState("co-001");
  const [generating, setGenerating] = useState(false);
  const isAr = lang === "ar";
  const dir = isAr ? "rtl" : "ltr";

  const currentDate = new Date();
  const month = currentDate.toLocaleString("en-AE", { month: "long" });
  const year = currentDate.getFullYear();

  const mockPayslips = [
    { id: "001", name_en: "Ahmed Al-Rashidi", name_ar: "أحمد الراشدي",
      basic: "12,000", allowances: "4,500", deductions: "10", net: "16,490",
      iloe: "10", status: "pending" },
    { id: "002", name_en: "Priya Sharma", name_ar: "بريا شارما",
      basic: "8,000", allowances: "3,000", deductions: "5", net: "10,995",
      iloe: "5", status: "pending" },
    { id: "003", name_en: "Juan Santos", name_ar: "خوان سانتوس",
      basic: "5,000", allowances: "2,300", deductions: "5", net: "7,295",
      iloe: "5", status: "pending" },
  ];

  const handleGenerate = async () => {
    setGenerating(true);
    await new Promise(r => setTimeout(r, 2000));
    setGenerating(false);
    alert(isAr ? "تم إنشاء الرواتب بنجاح!" : "Payroll generated successfully!");
  };

  return (
    <div className={`min-h-screen p-6 ${darkMode ? "bg-gray-900 text-white" : "bg-gray-50"}`} dir={dir}>

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {isAr ? "الرواتب — الإمارات (درهم)" : "UAE Payroll — AED"}
          </h1>
          <p className="text-sm text-gray-500">
            {month} {year} · {isAr ? "الشركة" : "Company"}: {selectedCompany}
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

      {/* ── Status + actions ────────────────────────────────────────────────── */}
      <div className={`rounded-lg border p-4 mb-6 flex items-center justify-between ${
        darkMode ? "bg-gray-800 border-gray-700" : "bg-white"
      }`}>
        <div>
          <p className="text-sm font-medium">{isAr ? "الحالة:" : "Status:"}</p>
          <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
            {isAr ? "⏳ لم يتم الإنشاء بعد" : "⏳ Not Generated Yet"}
          </span>
        </div>
        <div className="flex gap-2">
          <Button
            className="bg-blue-600 hover:bg-blue-700 text-white"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? (isAr ? "جارٍ الإنشاء..." : "Generating...") : (isAr ? "💰 إنشاء الرواتب" : "💰 Generate Payroll")}
          </Button>
          <Button className="bg-green-600 hover:bg-green-700 text-white">
            🏦 {isAr ? "تحميل ملف WPS" : "Download WPS SIF"}
          </Button>
          <Button variant="outline">
            ✅ {isAr ? "التحقق من WPS" : "Validate WPS"}
          </Button>
        </div>
      </div>

      {/* ── Totals row ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: isAr ? "إجمالي الرواتب" : "Total Gross", value: "AED 432,750", color: "blue" },
          { label: isAr ? "صافي الرواتب" : "Total Net", value: "AED 427,200", color: "green" },
          { label: isAr ? "إجمالي الخصومات" : "Total Deductions", value: "AED 5,550", color: "orange" },
          { label: isAr ? "إجمالي ILOE" : "Total ILOE", value: "AED 270", color: "purple" },
        ].map((s) => (
          <div key={s.label} className={`bg-white rounded-lg p-4 shadow-sm ${darkMode ? "!bg-gray-800" : ""}`}>
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className="text-lg font-bold mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      {/* ── Payroll table ────────────────────────────────────────────────────── */}
      <div className={`rounded-lg border overflow-hidden ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
        <table className="w-full text-sm">
          <thead className={darkMode ? "bg-gray-700" : "bg-gray-50"}>
            <tr>
              <th className="text-left px-4 py-3">{isAr ? "اسم الموظف" : "Employee"}</th>
              <th className="text-right px-4 py-3">{isAr ? "الراتب الأساسي" : "Basic (AED)"}</th>
              <th className="text-right px-4 py-3">{isAr ? "البدلات" : "Allowances (AED)"}</th>
              <th className="text-right px-4 py-3">{isAr ? "ILOE" : "ILOE (AED)"}</th>
              <th className="text-right px-4 py-3">{isAr ? "الخصومات" : "Deductions (AED)"}</th>
              <th className="text-right px-4 py-3 font-bold">{isAr ? "الصافي" : "Net (AED)"}</th>
              <th className="text-center px-4 py-3">{isAr ? "الحالة" : "Status"}</th>
            </tr>
          </thead>
          <tbody>
            {mockPayslips.map((p) => (
              <tr key={p.id} className={`border-t ${darkMode ? "border-gray-700" : "border-gray-100"}`}>
                <td className="px-4 py-3 font-medium">
                  {isAr ? p.name_ar : p.name_en}
                </td>
                <td className="px-4 py-3 text-right">{p.basic}</td>
                <td className="px-4 py-3 text-right">{p.allowances}</td>
                <td className="px-4 py-3 text-right text-red-600">-{p.iloe}</td>
                <td className="px-4 py-3 text-right text-red-600">-{p.deductions}</td>
                <td className="px-4 py-3 text-right font-bold text-green-600">{p.net}</td>
                <td className="px-4 py-3 text-center">
                  <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                    {isAr ? "معلق" : "Pending"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── WPS info note ────────────────────────────────────────────────────── */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg text-xs text-blue-700">
        {isAr
          ? "ملاحظة: ILOE إلزامي منذ يناير 2023 — AED 5/شهر (راتب أقل من 16,000) أو AED 10/شهر (راتب 16,000 أو أكثر). لا توجد ضريبة دخل في الإمارات."
          : "Note: ILOE is mandatory since January 2023 — AED 5/month (basic < AED 16,000) or AED 10/month (basic ≥ AED 16,000). No income tax in UAE."}
      </div>
    </div>
  );
}
