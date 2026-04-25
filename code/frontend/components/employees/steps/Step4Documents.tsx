"use client";

import React, { useRef, useState } from "react";
import { UseFormReturn, useWatch } from "react-hook-form";
import { AddEmployeeFormData } from "@/schemas/employee.schema";

interface Props {
  form: UseFormReturn<AddEmployeeFormData>;
}

type DocKey =
  | "cnic_front"
  | "cnic_back"
  | "passport_file"
  | "degree_certificate"
  | "experience_letter"
  | "cv_resume"
  | "signed_offer_letter"
  | "contract_file"
  | "medical_fitness_certificate";

interface UploadBoxProps {
  label: string;
  fieldKey: DocKey;
  required?: boolean;
  accept?: string;
  hint?: string;
  form: UseFormReturn<AddEmployeeFormData>;
}

function UploadBox({ label, fieldKey, required, accept = "application/pdf,image/*", hint, form }: UploadBoxProps) {
  const { setValue, formState: { errors } } = form;
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      alert(`${label}: File must be under 5MB`);
      return;
    }
    setValue(fieldKey as keyof AddEmployeeFormData, file as never);
    setFileName(file.name);
  };

  const error = errors[fieldKey as keyof typeof errors] as { message?: string } | undefined;

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <div
        onClick={() => inputRef.current?.click()}
        className={`
          flex items-center gap-3 rounded-lg border-2 border-dashed px-4 py-3 cursor-pointer transition-colors
          ${fileName
            ? "border-green-300 bg-green-50"
            : error
            ? "border-red-300 bg-red-50"
            : "border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50"
          }
        `}
      >
        {fileName ? (
          <>
            <svg className="w-5 h-5 text-green-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-green-700 truncate">{fileName}</p>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setFileName(null);
                  setValue(fieldKey as keyof AddEmployeeFormData, undefined as never);
                  if (inputRef.current) inputRef.current.value = "";
                }}
                className="text-xs text-red-500 hover:text-red-600"
              >
                Remove
              </button>
            </div>
          </>
        ) : (
          <>
            <svg className="w-5 h-5 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <div>
              <p className="text-sm text-gray-600">Click to upload</p>
              {hint && <p className="text-xs text-gray-400">{hint}</p>}
            </div>
          </>
        )}
      </div>
      <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={handleChange} />
      {error?.message && (
        <p className="mt-1 text-xs text-red-600">{error.message}</p>
      )}
    </div>
  );
}

export default function Step4Documents({ form }: Props) {
  const { register, setValue, formState: { errors }, control } = form;
  const hasPassport = useWatch({ control, name: "has_passport" });

  return (
    <div className="space-y-8">
      {/* ── CNIC / NID Documents ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          CNIC / National ID
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <UploadBox
            label="CNIC Front"
            fieldKey="cnic_front"
            hint="JPG, PNG or PDF · max 5MB"
            form={form}
          />
          <UploadBox
            label="CNIC Back"
            fieldKey="cnic_back"
            hint="JPG, PNG or PDF · max 5MB"
            form={form}
          />
        </div>
      </div>

      {/* ── Passport ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Passport
        </h3>
        <label className="flex items-center gap-2 cursor-pointer mb-4">
          <input
            {...register("has_passport")}
            type="checkbox"
            className="w-4 h-4 rounded text-blue-600 border-gray-300 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Employee has a passport</span>
        </label>

        {hasPassport && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 pl-6 border-l-2 border-blue-100">
            <FormField label="Passport Number" error={errors.passport_number?.message}>
              <input
                {...register("passport_number")}
                type="text"
                placeholder="AB1234567"
                className={inputClass(errors.passport_number)}
              />
            </FormField>
            <FormField label="Passport Expiry" error={errors.passport_expiry?.message}>
              <input
                {...register("passport_expiry")}
                type="date"
                className={inputClass(errors.passport_expiry)}
              />
            </FormField>
            <div className="sm:col-span-2">
              <UploadBox
                label="Passport Scan"
                fieldKey="passport_file"
                hint="Photo page · PDF or JPG · max 5MB"
                form={form}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Education ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Educational Qualification
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Highest Qualification" error={errors.highest_qualification?.message}>
            <select
              {...register("highest_qualification")}
              className={inputClass(errors.highest_qualification)}
            >
              <option value="">Select qualification</option>
              <option value="matric">Matric (10th)</option>
              <option value="intermediate">Intermediate (12th)</option>
              <option value="diploma">Diploma</option>
              <option value="bachelors">Bachelor's Degree</option>
              <option value="masters">Master's Degree</option>
              <option value="phd">PhD / Doctorate</option>
              <option value="other">Other</option>
            </select>
          </FormField>

          <div>
            <UploadBox
              label="Degree / Certificate"
              fieldKey="degree_certificate"
              hint="PDF or JPG · max 5MB"
              form={form}
            />
          </div>
        </div>
      </div>

      {/* ── Professional Documents ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Professional Documents
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <UploadBox
            label="CV / Resume"
            fieldKey="cv_resume"
            accept="application/pdf,.doc,.docx"
            hint="PDF or Word · max 5MB"
            form={form}
          />
          <UploadBox
            label="Experience Letter(s)"
            fieldKey="experience_letter"
            hint="PDF or JPG · max 5MB"
            form={form}
          />
        </div>
      </div>

      {/* ── Employment Documents ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Employment Documents
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <UploadBox
            label="Signed Offer Letter"
            fieldKey="signed_offer_letter"
            hint="PDF · max 5MB"
            form={form}
          />
          <UploadBox
            label="Employment Contract"
            fieldKey="contract_file"
            hint="PDF · max 5MB"
            form={form}
          />
        </div>
      </div>

      {/* ── Medical ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Medical Fitness
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <UploadBox
            label="Medical Fitness Certificate"
            fieldKey="medical_fitness_certificate"
            hint="PDF or JPG · max 5MB"
            form={form}
          />
          <FormField label="Medical Certificate Expiry" error={errors.medical_expiry?.message}>
            <input
              {...register("medical_expiry")}
              type="date"
              className={inputClass(errors.medical_expiry)}
            />
          </FormField>
        </div>
      </div>

      {/* ── Visa / Work Permit (non-nationals) ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Visa & Work Permit
          <span className="ml-2 text-xs font-normal text-gray-400 normal-case tracking-normal">
            (For foreign nationals only)
          </span>
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField label="Visa Number" error={errors.visa_number?.message}>
            <input
              {...register("visa_number")}
              type="text"
              placeholder="Optional"
              className={inputClass(errors.visa_number)}
            />
          </FormField>

          <FormField label="Visa Type" error={errors.visa_type?.message}>
            <input
              {...register("visa_type")}
              type="text"
              placeholder="e.g. Work Visa"
              className={inputClass(errors.visa_type)}
            />
          </FormField>

          <FormField label="Visa Expiry" error={errors.visa_expiry?.message}>
            <input
              {...register("visa_expiry")}
              type="date"
              className={inputClass(errors.visa_expiry)}
            />
          </FormField>

          <FormField label="Work Permit Number" error={errors.work_permit_number?.message}>
            <input
              {...register("work_permit_number")}
              type="text"
              placeholder="Optional"
              className={inputClass(errors.work_permit_number)}
            />
          </FormField>

          <FormField label="Work Permit Expiry" error={errors.work_permit_expiry?.message}>
            <input
              {...register("work_permit_expiry")}
              type="date"
              className={inputClass(errors.work_permit_expiry)}
            />
          </FormField>
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function inputClass(error?: { message?: string }) {
  const base =
    "block w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm transition-colors focus:outline-none focus:ring-2";
  return error
    ? `${base} border-red-300 bg-red-50 text-red-900 focus:border-red-400 focus:ring-red-200`
    : `${base} border-gray-300 bg-white text-gray-900 focus:border-blue-400 focus:ring-blue-100`;
}

function FormField({
  label,
  required,
  hint,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
      {error && (
        <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}
