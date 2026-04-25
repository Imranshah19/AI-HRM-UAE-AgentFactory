"use client";

import React, { useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  addEmployeeSchema,
  basicInfoSchema,
  employmentSchema,
  compensationSchema,
  documentsSchema,
  accessSchema,
  AddEmployeeFormData,
} from "@/schemas/employee.schema";
import {
  Department,
  Branch,
  Employee,
  Role,
  Shift,
  SalaryStructure,
  FormStep,
  CreateEmployeeResponse,
} from "@/types/employee.types";

import Step1BasicInfo    from "./steps/Step1BasicInfo";
import Step2Employment   from "./steps/Step2Employment";
import Step3Compensation from "./steps/Step3Compensation";
import Step4Documents    from "./steps/Step4Documents";
import Step5Access       from "./steps/Step5Access";

// ─── Step Definitions ─────────────────────────────────────────────────────────

const STEP_DEFS: Omit<FormStep, "isCompleted" | "hasError">[] = [
  { id: 1, key: "basic_info",    label: "Basic Info",    description: "Personal & contact details",  icon: "👤" },
  { id: 2, key: "employment",    label: "Employment",    description: "Role, department & schedule",  icon: "🏢" },
  { id: 3, key: "compensation",  label: "Compensation",  description: "Salary, allowances & bank",    icon: "💰" },
  { id: 4, key: "documents",     label: "Documents",     description: "Upload required documents",    icon: "📄" },
  { id: 5, key: "access",        label: "Access",        description: "System roles & permissions",   icon: "🔐" },
];

const STEP_SCHEMAS = [basicInfoSchema, employmentSchema, compensationSchema, documentsSchema, accessSchema];

// ─── Props ────────────────────────────────────────────────────────────────────

interface AddEmployeeFormProps {
  departments:      Department[];
  branches:         Branch[];
  managers:         Employee[];
  employees:        Employee[];
  roles:            Role[];
  shifts:           Shift[];
  salaryStructures: SalaryStructure[];
  onSuccess?:       (result: CreateEmployeeResponse) => void;
  onCancel?:        () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function AddEmployeeForm({
  departments,
  branches,
  managers,
  employees,
  roles,
  shifts,
  salaryStructures,
  onSuccess,
  onCancel,
}: AddEmployeeFormProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<AddEmployeeFormData>({
    resolver: zodResolver(addEmployeeSchema),
    mode: "onTouched",
    defaultValues: {
      // Personal defaults
      country: "Pakistan",
      nationality: "Pakistani",
      marital_status: undefined,
      // Employment defaults
      work_schedule: "full_time",
      work_location: "office",
      timezone: "Asia/Karachi",
      notice_period_days: 30,
      // Compensation defaults
      currency: "PKR",
      house_rent_allowance: 0,
      medical_allowance: 0,
      transport_allowance: 0,
      fuel_allowance: 0,
      utility_allowance: 0,
      other_allowances: 0,
      eobi_applicable: true,
      sessi_applicable: false,
      income_tax_applicable: true,
      payment_method: "bank_transfer",
      // Documents defaults
      has_passport: false,
      // Access defaults
      create_work_email: true,
      laptop_required: false,
      sim_card_required: false,
      access_card_required: true,
      parking_slot_required: false,
      send_welcome_email: true,
      send_portal_credentials: true,
      modules_access: ["self_service", "attendance", "leave"],
    },
  });

  // ── Validate current step before advancing ────────────────────────────────

  const validateCurrentStep = useCallback(async (): Promise<boolean> => {
    const stepSchema = STEP_SCHEMAS[currentStep - 1];
    const values = form.getValues();
    const result = await stepSchema.safeParseAsync(values);

    if (!result.success) {
      // Trigger validation display for visible fields
      const fieldKeys = Object.keys(result.error.flatten().fieldErrors);
      fieldKeys.forEach((key) =>
        form.trigger(key as keyof AddEmployeeFormData)
      );
      return false;
    }
    return true;
  }, [currentStep, form]);

  const handleNext = async () => {
    const valid = await validateCurrentStep();
    if (!valid) return;
    setCompletedSteps((prev) => new Set(prev).add(currentStep));
    setCurrentStep((s) => Math.min(s + 1, 5));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleBack = () => {
    setCurrentStep((s) => Math.max(s - 1, 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleStepClick = async (stepId: number) => {
    if (stepId < currentStep) {
      setCurrentStep(stepId);
      return;
    }
    if (stepId === currentStep + 1) {
      await handleNext();
    }
  };

  // ── Form Submission ───────────────────────────────────────────────────────

  const handleSubmit = form.handleSubmit(async (data) => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const formData = new FormData();

      // Append all scalar values
      Object.entries(data).forEach(([key, value]) => {
        if (value instanceof File) {
          formData.append(key, value);
        } else if (Array.isArray(value)) {
          value.forEach((v) => formData.append(`${key}[]`, String(v)));
        } else if (value !== undefined && value !== null) {
          formData.append(key, String(value));
        }
      });

      const response = await fetch("/api/employees", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to create employee");
      }

      const result: CreateEmployeeResponse = await response.json();
      onSuccess?.(result);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setIsSubmitting(false);
    }
  });

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Page Header ── */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Add New Employee</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Complete all steps to onboard a new team member
            </p>
          </div>
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* ── Stepper ── */}
        <nav className="mb-8">
          {/* Desktop stepper */}
          <ol className="hidden sm:flex items-center">
            {STEP_DEFS.map((step, idx) => {
              const isCompleted = completedSteps.has(step.id);
              const isCurrent   = currentStep === step.id;
              const isLast      = idx === STEP_DEFS.length - 1;

              return (
                <React.Fragment key={step.id}>
                  <li className="flex items-center">
                    <button
                      type="button"
                      onClick={() => handleStepClick(step.id)}
                      disabled={step.id > currentStep + 1}
                      className="flex items-center gap-3 group disabled:cursor-not-allowed"
                    >
                      {/* Step circle */}
                      <span className={`
                        flex items-center justify-center w-9 h-9 rounded-full text-sm font-semibold border-2 transition-all
                        ${isCompleted
                          ? "border-blue-600 bg-blue-600 text-white"
                          : isCurrent
                          ? "border-blue-600 bg-white text-blue-600"
                          : "border-gray-300 bg-white text-gray-400 group-hover:border-gray-400"
                        }
                      `}>
                        {isCompleted ? (
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          step.id
                        )}
                      </span>

                      {/* Step label */}
                      <span className="hidden lg:block text-left">
                        <span className={`block text-sm font-medium ${isCurrent ? "text-blue-700" : isCompleted ? "text-gray-700" : "text-gray-400"}`}>
                          {step.label}
                        </span>
                        <span className="block text-xs text-gray-400">{step.description}</span>
                      </span>
                    </button>
                  </li>

                  {/* Connector */}
                  {!isLast && (
                    <div className={`flex-1 h-0.5 mx-3 transition-colors ${isCompleted ? "bg-blue-600" : "bg-gray-200"}`} />
                  )}
                </React.Fragment>
              );
            })}
          </ol>

          {/* Mobile stepper */}
          <div className="flex sm:hidden items-center justify-between bg-white rounded-xl border border-gray-200 px-4 py-3">
            <span className="text-sm text-gray-500">Step {currentStep} of {STEP_DEFS.length}</span>
            <span className="text-sm font-semibold text-blue-700">{STEP_DEFS[currentStep - 1].label}</span>
            <span className="text-xs text-gray-400">{completedSteps.size} completed</span>
          </div>
        </nav>

        {/* ── Form Card ── */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          {/* Card header */}
          <div className="border-b border-gray-100 px-6 py-4 flex items-center gap-3">
            <span className="text-2xl">{STEP_DEFS[currentStep - 1].icon}</span>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{STEP_DEFS[currentStep - 1].label}</h2>
              <p className="text-sm text-gray-500">{STEP_DEFS[currentStep - 1].description}</p>
            </div>
          </div>

          {/* Form body */}
          <form onSubmit={handleSubmit} noValidate>
            <div className="px-6 py-6">
              {currentStep === 1 && <Step1BasicInfo form={form} />}
              {currentStep === 2 && (
                <Step2Employment
                  form={form}
                  departments={departments}
                  branches={branches}
                  managers={managers}
                  shifts={shifts}
                />
              )}
              {currentStep === 3 && <Step3Compensation form={form} salaryStructures={salaryStructures} />}
              {currentStep === 4 && <Step4Documents form={form} />}
              {currentStep === 5 && <Step5Access form={form} roles={roles} employees={employees} />}
            </div>

            {/* Submit Error */}
            {submitError && (
              <div className="mx-6 mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 flex items-start gap-2">
                <svg className="w-4 h-4 text-red-500 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <p className="text-sm text-red-700">{submitError}</p>
              </div>
            )}

            {/* ── Navigation Footer ── */}
            <div className="border-t border-gray-100 px-6 py-4 flex items-center justify-between bg-gray-50">
              <button
                type="button"
                onClick={handleBack}
                disabled={currentStep === 1}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back
              </button>

              <div className="flex items-center gap-2">
                {/* Step progress dots */}
                {STEP_DEFS.map((s) => (
                  <div
                    key={s.id}
                    className={`w-2 h-2 rounded-full transition-colors ${
                      completedSteps.has(s.id) ? "bg-blue-600" : s.id === currentStep ? "bg-blue-400" : "bg-gray-200"
                    }`}
                  />
                ))}
              </div>

              {currentStep < 5 ? (
                <button
                  type="button"
                  onClick={handleNext}
                  className="flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 active:bg-blue-800 transition-colors"
                >
                  Next
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-2 px-6 py-2 text-sm font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 active:bg-green-800 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                >
                  {isSubmitting ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Creating Employee...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Create Employee
                    </>
                  )}
                </button>
              )}
            </div>
          </form>
        </div>

        {/* ── Required fields note ── */}
        <p className="mt-3 text-xs text-gray-400 text-center">
          Fields marked with <span className="text-red-400">*</span> are required
        </p>
      </div>
    </div>
  );
}
