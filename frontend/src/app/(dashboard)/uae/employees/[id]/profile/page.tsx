"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";

// ─── Document status badge ─────────────────────────────────────────────────────

function DocStatusBadge({ days }: { days: number }) {
  if (days <= 0) return <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded-full">🔴 Expired</span>;
  if (days <= 14) return <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded-full">🔴 Critical</span>;
  if (days <= 30) return <span className="text-xs bg-orange-100 text-orange-800 px-2 py-0.5 rounded-full">🟡 Urgent</span>;
  if (days <= 90) return <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full">🟡 Expiring Soon</span>;
  return <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">🟢 Valid</span>;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function UAEEmployeeProfilePage() {
  const params = useParams();
  const employeeId = params.id as string;
  const [lang, setLang] = useState<"en" | "ar">("en");
  const isAr = lang === "ar";
  const dir = isAr ? "rtl" : "ltr";

  const today = new Date();
  const toDate = (s: string) => new Date(s);
  const daysUntil = (s: string) => Math.floor((toDate(s).getTime() - today.getTime()) / 86400000);

  // Mock employee data
  const emp = {
    name_en: "Ahmed Al-Rashidi",
    name_ar: "أحمد الراشدي",
    employee_id: employeeId,
    company: "Company A",
    department: "Technology",
    join_date: "2022-01-15",
    nationality: "UAE",
  };

  const documents = [
    { type: "passport",    name_en: "Passport",          name_ar: "جواز السفر",              expiry: "2028-05-15", number: "A1234567" },
    { type: "visa",        name_en: "UAE Residence Visa", name_ar: "تأشيرة الإقامة",         expiry: "2026-06-30", number: "UAE-987654" },
    { type: "emirates_id", name_en: "Emirates ID",        name_ar: "الهوية الإماراتية",       expiry: "2026-06-30", number: "784-1990-1234567-8" },
    { type: "labour_card", name_en: "Labour Card",        name_ar: "بطاقة العمل",             expiry: "2026-06-30", number: "CN-12345678" },
    { type: "insurance",   name_en: "Medical Insurance",  name_ar: "التأمين الصحي",           expiry: "2026-12-31", number: "DAM-12345" },
  ];

  const salary = {
    basic: "12,000", housing: "3,000", transport: "800",
    food: "500", other: "200", total: "16,500",
    iloe: "10", net_est: "16,490",
  };

  const gratuity = {
    service_years: "4.29",
    current_aed: "35,700",
    projected_at_expiry_aed: "42,000",
  };

  const leaveBalance = [
    { type: "Annual", type_ar: "سنوية", entitled: 30, used: 8, balance: 22 },
    { type: "Sick",   type_ar: "مرضية",  entitled: 15, used: 2, balance: 13 },
    { type: "Paternity", type_ar: "أبوة", entitled: 5, used: 0, balance: 5 },
    { type: "Hajj",   type_ar: "حج",     entitled: 30, used: 0, balance: 30 },
    { type: "Study",  type_ar: "دراسية", entitled: 10, used: 0, balance: 10 },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6" dir={dir}>

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center text-2xl">
            👤
          </div>
          <div>
            <h1 className="text-2xl font-bold">{isAr ? emp.name_ar : emp.name_en}</h1>
            <p className="text-sm text-gray-500">{emp.company} · {emp.department}</p>
            <p className="text-xs text-gray-400">
              {isAr ? "تاريخ الانضمام:" : "Joined:"} {emp.join_date}
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => setLang(isAr ? "en" : "ar")}>
          {isAr ? "EN" : "عربي"}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* ── Documents section ──────────────────────────────────────────────── */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold mb-4">
            {isAr ? "📄 الوثائق" : "📄 Documents"}
          </h2>
          <div className="space-y-3">
            {documents.map((doc) => (
              <div key={doc.type} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <p className="text-sm font-medium">{isAr ? doc.name_ar : doc.name_en}</p>
                  <p className="text-xs text-gray-500">{doc.number} · {isAr ? "تنتهي" : "Expires"}: {doc.expiry}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{daysUntil(doc.expiry)}d</span>
                  <DocStatusBadge days={daysUntil(doc.expiry)} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Gratuity widget ────────────────────────────────────────────────── */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold mb-4">
            {isAr ? "💰 حاسبة المكافأة" : "💰 Gratuity Calculator"}
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-sm text-gray-600">{isAr ? "سنوات الخدمة" : "Service Years"}</span>
              <span className="font-semibold">{gratuity.service_years} {isAr ? "سنة" : "years"}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-sm text-gray-600">{isAr ? "المكافأة الحالية" : "Current Gratuity"}</span>
              <span className="font-bold text-green-600">AED {gratuity.current_aed}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-sm text-gray-600">{isAr ? "المتوقع عند انتهاء العقد" : "Projected at Contract End"}</span>
              <span className="font-semibold text-blue-600">AED {gratuity.projected_at_expiry_aed}</span>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-3">
            {isAr ? "وفق المرسوم الاتحادي رقم 33/2021" : "Per Federal Decree-Law No. 33/2021"}
          </p>
        </div>

        {/* ── Leave balance ──────────────────────────────────────────────────── */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold mb-4">
            {isAr ? "📅 أرصدة الإجازات" : "📅 Leave Balances"}
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs">
                <th className="text-left py-1">{isAr ? "النوع" : "Type"}</th>
                <th className="text-center">{isAr ? "المستحق" : "Entitled"}</th>
                <th className="text-center">{isAr ? "المستخدم" : "Used"}</th>
                <th className="text-center">{isAr ? "الرصيد" : "Balance"}</th>
              </tr>
            </thead>
            <tbody>
              {leaveBalance.map((lb) => (
                <tr key={lb.type} className="border-t border-gray-50">
                  <td className="py-1.5 font-medium">{isAr ? lb.type_ar : lb.type}</td>
                  <td className="text-center text-gray-600">{lb.entitled}</td>
                  <td className="text-center text-orange-600">{lb.used}</td>
                  <td className="text-center font-bold text-green-600">{lb.balance}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ── Salary structure ───────────────────────────────────────────────── */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold mb-4">
            {isAr ? "💵 هيكل الراتب (درهم)" : "💵 Salary Structure (AED)"}
          </h2>
          <div className="space-y-2">
            {[
              { label: isAr ? "الراتب الأساسي" : "Basic Salary", value: salary.basic },
              { label: isAr ? "بدل السكن" : "Housing Allowance", value: salary.housing },
              { label: isAr ? "بدل التنقل" : "Transport Allowance", value: salary.transport },
              { label: isAr ? "بدل الطعام" : "Food Allowance", value: salary.food },
              { label: isAr ? "بدلات أخرى" : "Other Allowances", value: salary.other },
            ].map((item) => (
              <div key={item.label} className="flex justify-between text-sm py-1 border-b border-gray-50">
                <span className="text-gray-600">{item.label}</span>
                <span className="font-medium">AED {item.value}</span>
              </div>
            ))}
            <div className="flex justify-between text-sm py-1 border-t-2 border-gray-200 mt-2">
              <span className="font-bold">{isAr ? "إجمالي الحزمة" : "Total Package"}</span>
              <span className="font-bold text-blue-600">AED {salary.total}</span>
            </div>
            <div className="flex justify-between text-xs py-1 text-red-600">
              <span>{isAr ? "خصم ILOE (إلزامي)" : "ILOE Deduction (mandatory)"}</span>
              <span>- AED {salary.iloe}/month</span>
            </div>
            <div className="flex justify-between text-sm py-1 font-bold text-green-600">
              <span>{isAr ? "صافي الراتب المتوقع" : "Estimated Net Salary"}</span>
              <span>AED {salary.net_est}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
