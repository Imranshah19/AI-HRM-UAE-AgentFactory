import { z } from "zod";

// ─── Step 1: Basic Info ───────────────────────────────────────────────────────
export const basicInfoSchema = z.object({
  // Personal
  first_name: z.string().min(2, "First name must be at least 2 characters"),
  last_name: z.string().min(2, "Last name must be at least 2 characters"),
  middle_name: z.string().optional(),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  gender: z.enum(["male", "female", "other", "prefer_not_to_say"], {
    required_error: "Gender is required",
  }),
  marital_status: z.enum(["single", "married", "divorced", "widowed"]).optional(),
  nationality: z.string().min(1, "Nationality is required"),
  cnic_nid: z
    .string()
    .min(1, "CNIC/NID is required")
    .regex(/^\d{5}-\d{7}-\d$/, "Format: 12345-1234567-1"),
  cnic_expiry: z.string().optional(),
  personal_email: z.string().email("Invalid email address"),
  phone_primary: z
    .string()
    .min(10, "Phone number too short")
    .regex(/^\+?[\d\s\-()]+$/, "Invalid phone number"),
  phone_secondary: z
    .string()
    .regex(/^\+?[\d\s\-()]*$/, "Invalid phone number")
    .optional()
    .or(z.literal("")),
  // Address
  address_line1: z.string().min(5, "Address is required"),
  address_line2: z.string().optional(),
  city: z.string().min(2, "City is required"),
  state_province: z.string().min(2, "State/Province is required"),
  postal_code: z.string().min(3, "Postal code is required"),
  country: z.string().min(2, "Country is required"),
  // Emergency Contact
  emergency_contact_name: z.string().min(2, "Emergency contact name is required"),
  emergency_contact_relation: z.string().min(2, "Relation is required"),
  emergency_contact_phone: z
    .string()
    .min(10, "Emergency contact phone is required"),
  emergency_contact_email: z.string().email("Invalid email").optional().or(z.literal("")),
  // Photo
  profile_photo: z.instanceof(File).optional(),
});

// ─── Step 2: Employment ──────────────────────────────────────────────────────
export const employmentSchema = z.object({
  employee_id: z.string().min(1, "Employee ID is required"),
  work_email: z.string().email("Invalid work email"),
  designation: z.string().min(2, "Designation is required"),
  department_id: z.string().min(1, "Department is required"),
  branch_id: z.string().min(1, "Branch/Location is required"),
  reporting_manager_id: z.string().min(1, "Reporting manager is required"),
  contract_type: z.enum(["permanent", "fixed_term", "probation", "intern", "consultant"], {
    required_error: "Contract type is required",
  }),
  joining_date: z.string().min(1, "Joining date is required"),
  probation_end_date: z.string().optional(),
  confirmation_date: z.string().optional(),
  work_schedule: z.enum(["full_time", "part_time", "remote", "hybrid"], {
    required_error: "Work schedule is required",
  }),
  shift_id: z.string().optional(),
  notice_period_days: z.number({ coerce: true }).min(0).default(30),
  grade_level: z.string().optional(),
  cost_center: z.string().optional(),
  work_location: z.enum(["office", "remote", "hybrid", "field"]).default("office"),
  timezone: z.string().default("Asia/Karachi"),
});

// ─── Step 3: Compensation ────────────────────────────────────────────────────
export const compensationSchema = z.object({
  currency: z.string().default("PKR"),
  basic_salary: z.number({ coerce: true }).min(1, "Basic salary is required"),
  house_rent_allowance: z.number({ coerce: true }).min(0).default(0),
  medical_allowance: z.number({ coerce: true }).min(0).default(0),
  transport_allowance: z.number({ coerce: true }).min(0).default(0),
  fuel_allowance: z.number({ coerce: true }).min(0).default(0),
  utility_allowance: z.number({ coerce: true }).min(0).default(0),
  other_allowances: z.number({ coerce: true }).min(0).default(0),
  // Deductions
  eobi_applicable: z.boolean().default(true),
  sessi_applicable: z.boolean().default(false),
  income_tax_applicable: z.boolean().default(true),
  // Bank Details
  bank_name: z.string().min(2, "Bank name is required"),
  bank_account_title: z.string().min(2, "Account title is required"),
  bank_account_number: z.string().min(8, "Account number is required"),
  bank_iban: z.string().optional(),
  bank_branch_code: z.string().optional(),
  payment_method: z.enum(["bank_transfer", "cash", "cheque"]).default("bank_transfer"),
  // Salary Structure
  salary_structure_id: z.string().optional(),
  effective_date: z.string().min(1, "Effective date is required"),
});

// ─── Step 4: Documents ───────────────────────────────────────────────────────
export const documentsSchema = z.object({
  // CNIC
  cnic_front: z.instanceof(File).optional(),
  cnic_back: z.instanceof(File).optional(),
  // Passport
  has_passport: z.boolean().default(false),
  passport_number: z.string().optional(),
  passport_expiry: z.string().optional(),
  passport_file: z.instanceof(File).optional(),
  // Educational
  highest_qualification: z.enum([
    "matric", "intermediate", "bachelors", "masters", "phd", "diploma", "other",
  ]).optional(),
  degree_certificate: z.instanceof(File).optional(),
  // Professional
  experience_letter: z.instanceof(File).optional(),
  cv_resume: z.instanceof(File).optional(),
  // Offer
  signed_offer_letter: z.instanceof(File).optional(),
  contract_file: z.instanceof(File).optional(),
  // Medical
  medical_fitness_certificate: z.instanceof(File).optional(),
  medical_expiry: z.string().optional(),
  // Additional
  additional_documents: z
    .array(
      z.object({
        doc_type: z.string(),
        doc_name: z.string(),
        expiry_date: z.string().optional(),
        file: z.instanceof(File).optional(),
      })
    )
    .optional(),
  // Visa (for non-nationals)
  visa_number: z.string().optional(),
  visa_type: z.string().optional(),
  visa_expiry: z.string().optional(),
  work_permit_number: z.string().optional(),
  work_permit_expiry: z.string().optional(),
});

// ─── Step 5: System Access ───────────────────────────────────────────────────
export const accessSchema = z.object({
  role_id: z.string().min(1, "Role is required"),
  // Email & Communication
  create_work_email: z.boolean().default(true),
  email_group_ids: z.array(z.string()).optional(),
  // System Access
  modules_access: z.array(z.string()).min(1, "At least one module access is required"),
  // IT Assets
  laptop_required: z.boolean().default(false),
  sim_card_required: z.boolean().default(false),
  access_card_required: z.boolean().default(true),
  parking_slot_required: z.boolean().default(false),
  // Onboarding
  send_welcome_email: z.boolean().default(true),
  send_portal_credentials: z.boolean().default(true),
  onboarding_checklist_template_id: z.string().optional(),
  buddy_employee_id: z.string().optional(),
  // Notes
  hr_notes: z.string().max(1000, "Notes must be under 1000 characters").optional(),
});

// ─── Combined Form Schema ─────────────────────────────────────────────────────
export const addEmployeeSchema = basicInfoSchema
  .merge(employmentSchema)
  .merge(compensationSchema)
  .merge(documentsSchema)
  .merge(accessSchema);

// ─── Types ────────────────────────────────────────────────────────────────────
export type BasicInfoFormData = z.infer<typeof basicInfoSchema>;
export type EmploymentFormData = z.infer<typeof employmentSchema>;
export type CompensationFormData = z.infer<typeof compensationSchema>;
export type DocumentsFormData = z.infer<typeof documentsSchema>;
export type AccessFormData = z.infer<typeof accessSchema>;
export type AddEmployeeFormData = z.infer<typeof addEmployeeSchema>;
