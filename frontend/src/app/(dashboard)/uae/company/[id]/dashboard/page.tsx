"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// ─── Status badge helper ───────────────────────────────────────────────────────

function StatusBadge({ ok, labelOk, labelFail }: { ok: boolean; labelOk: string; labelFail: string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
      ok ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
    }`}>
      {ok ? "✅" : "❌"} {ok ? labelOk : labelFail}
    </span>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CompanyDashboardPage() {
  const params = useParams();
  const companyId = params.id as string;
  const [lang, setLang] = useState<"en" | "ar">("en");
  const [darkMode, setDarkMode] = useState(false);
  const isAr = lang === "ar";
  const dir = isAr ? "rtl" : "ltr";

  const todayGregorian = new Date().toLocaleDateString("en-AE", {
    day: "2-digit", month: "short", year: "numeric",
  });

  // Mock data — replace with SWR/useQuery hook in production
  const company = {
    id: companyId,
    name_en: "Gulf Holdings — Company A",
    name_ar: "خليج هولدينج — الشركة أ",
    emirate: "Dubai",
    industry_type: "Technology",
    is_freezone: true,
    freezone_name: "DMCC",
  };

  const stats = {
    total_employees: 55, on_leave_today: 3,
    on_probation: 4, expiring_docs: 7,
  };

  const compliance = {
    wps_submitted: true, wps_date: "2026-03-28",
    emiratisation_pct: "3.64", emiratisation_target: "4.00",
    emiratisation_compliant: false, emiratisation_gap: 1,
    documents_expiring_30d: 7, contracts_expiring_90d: 2, insurance_expiring_30d: 5,
  };

  return (
    <div className={`min-h-screen p-6 ${darkMode ? "bg-gray-900 text-white" : "bg-gray-50"}`} dir={dir}>

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Button variant="ghost" size="sm" onClick={() => history.back()}>← {isAr ? "رجوع" : "Back"}</Button>
          </div>
          <h1 className="text-2xl font-bold">
            {isAr ? company.name_ar : company.name_en}
          </h1>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-sm text-gray-500">{company.emirate}</span>
            <span className="text-gray-300">|</span>
            <span className="text-sm text-gray-500">{company.industry_type}</span>
            {company.is_freezone && (
              <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                {company.freezone_name} {isAr ? "منطقة حرة" : "Free Zone"}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">{todayGregorian}</p>
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

      {/* ── Stats row ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: isAr ? "إجمالي الموظفين" : "Total Employees", value: stats.total_employees, color: "blue" },
          { label: isAr ? "في إجازة اليوم" : "On Leave Today", value: stats.on_leave_today, color: "yellow" },
          { label: isAr ? "في الاختبار" : "On Probation", value: stats.on_probation, color: "purple" },
          { label: isAr ? "وثائق منتهية قريباً" : "Docs Expiring (30d)", value: stats.expiring_docs, color: "red" },
        ].map((s) => (
          <div key={s.label} className={`bg-white rounded-lg p-4 shadow-sm border-l-4 ${
            s.color === "blue" ? "border-blue-500" :
            s.color === "yellow" ? "border-yellow-500" :
            s.color === "purple" ? "border-purple-500" : "border-red-500"
          } ${darkMode ? "!bg-gray-800" : ""}`}>
            <p className="text-sm text-gray-500">{s.label}</p>
            <p className="text-2xl font-bold mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      {/* ── Quick actions ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-3 mb-6">
        <Button className="bg-blue-600 hover:bg-blue-700 text-white">
          💰 {isAr ? "تشغيل الرواتب" : "Run Payroll"}
        </Button>
        <Button className="bg-green-600 hover:bg-green-700 text-white">
          📄 {isAr ? "فحص الوثائق" : "Check Documents"}
        </Button>
        <Button className="bg-purple-600 hover:bg-purple-700 text-white">
          🏦 {isAr ? "توليد ملف WPS" : "Generate WPS File"}
        </Button>
      </div>

      {/* ── Compliance scorecard ──────────────────────────────────────────── */}
      <div className={`rounded-lg border p-5 ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
        <h2 className="text-lg font-semibold mb-4">
          {isAr ? "بطاقة الامتثال" : "Compliance Scorecard"}
        </h2>

        <div className="space-y-3">
          <ComplianceRow
            icon="🏦"
            title={isAr ? "WPS — حماية الأجور" : "WPS — Wage Protection System"}
            status={<StatusBadge ok={compliance.wps_submitted} labelOk="Submitted ✅" labelFail="Not Submitted ❌" />}
            detail={isAr ? `آخر تقديم: ${compliance.wps_date}` : `Last submission: ${compliance.wps_date}`}
          />
          <ComplianceRow
            icon="🇦🇪"
            title={isAr ? "التوطين (الإماراتيون)" : "Emiratisation"}
            status={
              <StatusBadge
                ok={compliance.emiratisation_compliant}
                labelOk="Compliant ✅"
                labelFail={`Non-Compliant ❌ (gap: ${compliance.emiratisation_gap})`}
              />
            }
            detail={`${compliance.emiratisation_pct}% / ${compliance.emiratisation_target}% ${isAr ? "مطلوب" : "required"}`}
          />
          <ComplianceRow
            icon="📄"
            title={isAr ? "الوثائق المنتهية" : "Expiring Documents"}
            status={
              <span className={`text-sm font-medium ${compliance.documents_expiring_30d > 0 ? "text-orange-600" : "text-green-600"}`}>
                {compliance.documents_expiring_30d > 0 ? `⚠️ ${compliance.documents_expiring_30d} expiring in 30 days` : "✅ All valid"}
              </span>
            }
            detail=""
          />
          <ComplianceRow
            icon="📋"
            title={isAr ? "العقود المنتهية" : "Expiring Contracts"}
            status={
              <span className={`text-sm font-medium ${compliance.contracts_expiring_90d > 0 ? "text-yellow-600" : "text-green-600"}`}>
                {compliance.contracts_expiring_90d > 0 ? `⚠️ ${compliance.contracts_expiring_90d} in 90 days` : "✅ All valid"}
              </span>
            }
            detail=""
          />
          <ComplianceRow
            icon="🏥"
            title={isAr ? "التأمين الصحي" : "Medical Insurance"}
            status={
              <span className={`text-sm font-medium ${compliance.insurance_expiring_30d > 0 ? "text-orange-600" : "text-green-600"}`}>
                {compliance.insurance_expiring_30d > 0 ? `⚠️ ${compliance.insurance_expiring_30d} expiring in 30 days` : "✅ All insured"}
              </span>
            }
            detail=""
          />
        </div>
      </div>
    </div>
  );
}

function ComplianceRow({ icon, title, status, detail }: {
  icon: string; title: string; status: React.ReactNode; detail: string;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-2">
        <span>{icon}</span>
        <div>
          <p className="text-sm font-medium">{title}</p>
          {detail && <p className="text-xs text-gray-500">{detail}</p>}
        </div>
      </div>
      <div>{status}</div>
    </div>
  );
}
