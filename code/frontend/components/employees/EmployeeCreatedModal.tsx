"use client";

import React from "react";
import { CreateEmployeeResponse } from "@/types/employee.types";

interface Props {
  result: CreateEmployeeResponse;
  onClose: () => void;
  onAddAnother: () => void;
}

export default function EmployeeCreatedModal({ result, onClose, onAddAnother }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Green header */}
        <div className="bg-green-600 px-6 py-8 text-center">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white">Employee Created!</h2>
          <p className="text-green-100 text-sm mt-1">{result.message}</p>
        </div>

        {/* Details */}
        <div className="px-6 py-5 space-y-3">
          <DetailRow label="Employee ID"     value={result.employee_id} />
          <DetailRow label="Employee Number" value={result.employee_number} />
          {result.work_email && (
            <DetailRow label="Work Email" value={result.work_email} />
          )}
        </div>

        {/* Actions */}
        <div className="px-6 pb-6 flex flex-col gap-2">
          <button
            onClick={onClose}
            className="w-full py-2.5 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            View Employee Profile
          </button>
          <button
            onClick={onAddAnother}
            className="w-full py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Add Another Employee
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-gray-900">{value}</span>
    </div>
  );
}
