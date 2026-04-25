"use client";

import React, { useRef, useState } from "react";
import { UseFormReturn } from "react-hook-form";
import { AddEmployeeFormData } from "@/schemas/employee.schema";

interface Props {
  form: UseFormReturn<AddEmployeeFormData>;
}

const COUNTRIES = [
  "Pakistan", "India", "Bangladesh", "United Kingdom", "United States",
  "Canada", "Australia", "UAE", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain",
];

const NATIONALITIES = [
  "Pakistani", "Indian", "Bangladeshi", "British", "American", "Canadian",
  "Australian", "Emirati", "Saudi", "Qatari", "Kuwaiti", "Bahraini",
];

export default function Step1BasicInfo({ form }: Props) {
  const { register, formState: { errors }, watch, setValue } = form;
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      alert("Photo must be under 2MB");
      return;
    }
    setValue("profile_photo", file);
    const reader = new FileReader();
    reader.onload = () => setPhotoPreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  return (
    <div className="space-y-8">
      {/* ── Profile Photo ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Profile Photo
        </h3>
        <div className="flex items-center gap-6">
          <div
            className="w-24 h-24 rounded-full border-2 border-dashed border-gray-300 flex items-center justify-center bg-gray-50 cursor-pointer overflow-hidden hover:border-blue-400 transition-colors"
            onClick={() => photoInputRef.current?.click()}
          >
            {photoPreview ? (
              <img src={photoPreview} alt="Preview" className="w-full h-full object-cover" />
            ) : (
              <div className="text-center">
                <svg className="mx-auto h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span className="text-xs text-gray-400 mt-1 block">Upload</span>
              </div>
            )}
          </div>
          <div>
            <button
              type="button"
              onClick={() => photoInputRef.current?.click()}
              className="text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Choose photo
            </button>
            <p className="text-xs text-gray-500 mt-1">JPG, PNG up to 2MB. Square crop recommended.</p>
            {photoPreview && (
              <button
                type="button"
                onClick={() => { setPhotoPreview(null); setValue("profile_photo", undefined); }}
                className="text-xs text-red-500 hover:text-red-600 mt-1 block"
              >
                Remove
              </button>
            )}
          </div>
          <input
            ref={photoInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handlePhotoChange}
          />
        </div>
      </div>

      {/* ── Personal Information ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Personal Information
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField
            label="First Name"
            required
            error={errors.first_name?.message}
          >
            <input
              {...register("first_name")}
              type="text"
              placeholder="Muhammad"
              className={inputClass(errors.first_name)}
            />
          </FormField>

          <FormField label="Middle Name" error={errors.middle_name?.message}>
            <input
              {...register("middle_name")}
              type="text"
              placeholder="Optional"
              className={inputClass(errors.middle_name)}
            />
          </FormField>

          <FormField label="Last Name" required error={errors.last_name?.message}>
            <input
              {...register("last_name")}
              type="text"
              placeholder="Ahmed"
              className={inputClass(errors.last_name)}
            />
          </FormField>

          <FormField label="Date of Birth" required error={errors.date_of_birth?.message}>
            <input
              {...register("date_of_birth")}
              type="date"
              max={new Date(new Date().setFullYear(new Date().getFullYear() - 18))
                .toISOString()
                .split("T")[0]}
              className={inputClass(errors.date_of_birth)}
            />
          </FormField>

          <FormField label="Gender" required error={errors.gender?.message}>
            <select {...register("gender")} className={inputClass(errors.gender)}>
              <option value="">Select gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
            </select>
          </FormField>

          <FormField label="Marital Status" error={errors.marital_status?.message}>
            <select {...register("marital_status")} className={inputClass(errors.marital_status)}>
              <option value="">Select status</option>
              <option value="single">Single</option>
              <option value="married">Married</option>
              <option value="divorced">Divorced</option>
              <option value="widowed">Widowed</option>
            </select>
          </FormField>

          <FormField label="Nationality" required error={errors.nationality?.message}>
            <select {...register("nationality")} className={inputClass(errors.nationality)}>
              <option value="">Select nationality</option>
              {NATIONALITIES.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </FormField>

          <FormField
            label="CNIC / NID"
            required
            hint="Format: 12345-1234567-1"
            error={errors.cnic_nid?.message}
          >
            <input
              {...register("cnic_nid")}
              type="text"
              placeholder="12345-1234567-1"
              maxLength={15}
              className={inputClass(errors.cnic_nid)}
            />
          </FormField>

          <FormField label="CNIC Expiry Date" error={errors.cnic_expiry?.message}>
            <input
              {...register("cnic_expiry")}
              type="date"
              className={inputClass(errors.cnic_expiry)}
            />
          </FormField>
        </div>
      </div>

      {/* ── Contact Information ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Contact Information
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            label="Personal Email"
            required
            error={errors.personal_email?.message}
          >
            <input
              {...register("personal_email")}
              type="email"
              placeholder="name@gmail.com"
              className={inputClass(errors.personal_email)}
            />
          </FormField>

          <FormField
            label="Primary Phone"
            required
            error={errors.phone_primary?.message}
          >
            <input
              {...register("phone_primary")}
              type="tel"
              placeholder="+92 300 0000000"
              className={inputClass(errors.phone_primary)}
            />
          </FormField>

          <FormField
            label="Secondary Phone"
            error={errors.phone_secondary?.message}
          >
            <input
              {...register("phone_secondary")}
              type="tel"
              placeholder="+92 300 0000000 (optional)"
              className={inputClass(errors.phone_secondary)}
            />
          </FormField>
        </div>
      </div>

      {/* ── Address ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Residential Address
        </h3>
        <div className="grid grid-cols-1 gap-4">
          <FormField label="Address Line 1" required error={errors.address_line1?.message}>
            <input
              {...register("address_line1")}
              type="text"
              placeholder="House/Flat No., Street Name"
              className={inputClass(errors.address_line1)}
            />
          </FormField>
          <FormField label="Address Line 2" error={errors.address_line2?.message}>
            <input
              {...register("address_line2")}
              type="text"
              placeholder="Area, Block, Sector (optional)"
              className={inputClass(errors.address_line2)}
            />
          </FormField>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField label="City" required error={errors.city?.message}>
              <input
                {...register("city")}
                type="text"
                placeholder="Karachi"
                className={inputClass(errors.city)}
              />
            </FormField>
            <FormField label="State / Province" required error={errors.state_province?.message}>
              <input
                {...register("state_province")}
                type="text"
                placeholder="Sindh"
                className={inputClass(errors.state_province)}
              />
            </FormField>
            <FormField label="Postal Code" required error={errors.postal_code?.message}>
              <input
                {...register("postal_code")}
                type="text"
                placeholder="75000"
                className={inputClass(errors.postal_code)}
              />
            </FormField>
          </div>
          <FormField label="Country" required error={errors.country?.message}>
            <select {...register("country")} className={inputClass(errors.country)}>
              <option value="">Select country</option>
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </FormField>
        </div>
      </div>

      {/* ── Emergency Contact ── */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Emergency Contact
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormField
            label="Full Name"
            required
            error={errors.emergency_contact_name?.message}
          >
            <input
              {...register("emergency_contact_name")}
              type="text"
              placeholder="Contact full name"
              className={inputClass(errors.emergency_contact_name)}
            />
          </FormField>

          <FormField
            label="Relationship"
            required
            error={errors.emergency_contact_relation?.message}
          >
            <select
              {...register("emergency_contact_relation")}
              className={inputClass(errors.emergency_contact_relation)}
            >
              <option value="">Select relation</option>
              <option value="spouse">Spouse</option>
              <option value="parent">Parent</option>
              <option value="sibling">Sibling</option>
              <option value="child">Child</option>
              <option value="friend">Friend</option>
              <option value="other">Other</option>
            </select>
          </FormField>

          <FormField
            label="Phone Number"
            required
            error={errors.emergency_contact_phone?.message}
          >
            <input
              {...register("emergency_contact_phone")}
              type="tel"
              placeholder="+92 300 0000000"
              className={inputClass(errors.emergency_contact_phone)}
            />
          </FormField>

          <FormField
            label="Email Address"
            error={errors.emergency_contact_email?.message}
          >
            <input
              {...register("emergency_contact_email")}
              type="email"
              placeholder="contact@email.com (optional)"
              className={inputClass(errors.emergency_contact_email)}
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
      {hint && !error && (
        <p className="mt-1 text-xs text-gray-500">{hint}</p>
      )}
      {error && (
        <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}
