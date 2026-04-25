# SECTION 13 — NOTIFICATION TRIGGERS TABLE

| # | Event | Trigger Condition | Channel | Recipient | Template Variables | Retry Policy |
|---|---|---|---|---|---|---|
| 1 | Probation Ending (7-day) | `probation_end_date = TODAY + 7` | Email, In-App | Line Manager, HR | `{{employee_name}}`, `{{end_date}}`, `{{manager_name}}` | 3 retries, 1h apart |
| 2 | Probation Ending (1-day) | `probation_end_date = TOMORROW` | Email, SMS, In-App | Line Manager, HR | `{{employee_name}}`, `{{end_date}}` | 3 retries, 30min apart |
| 3 | Contract Expiry (30-day) | `contract_end_date = TODAY + 30` | Email, In-App | HR Manager | `{{employee_name}}`, `{{expiry_date}}`, `{{contract_type}}` | 2 retries, 2h apart |
| 4 | Contract Expiry (7-day) | `contract_end_date = TODAY + 7` | Email, SMS, In-App | HR Manager | `{{employee_name}}`, `{{expiry_date}}` | 3 retries, 1h apart |
| 5 | Passport Expiry (60-day) | `passport_expiry = TODAY + 60` | Email, In-App | Employee, HR | `{{employee_name}}`, `{{passport_number}}`, `{{expiry_date}}` | 2 retries, 4h apart |
| 6 | Visa Expiry (90-day) | `visa_expiry = TODAY + 90` | Email, SMS, In-App | Employee, HR | `{{employee_name}}`, `{{visa_type}}`, `{{expiry_date}}` | 2 retries, 4h apart |
| 7 | Leave Approved | Leave request status → approved | Email, In-App, Push | Employee | `{{employee_name}}`, `{{leave_type}}`, `{{start_date}}`, `{{end_date}}`, `{{approved_by}}` | 2 retries, 15min apart |
| 8 | Leave Rejected | Leave request status → rejected | Email, In-App, Push | Employee | `{{employee_name}}`, `{{leave_type}}`, `{{rejection_reason}}` | 2 retries, 15min apart |
| 9 | Leave Pending Approval | New leave request submitted | Email, In-App | Line Manager | `{{employee_name}}`, `{{leave_type}}`, `{{start_date}}`, `{{days}}`, `{{approval_link}}` | 3 retries, 30min apart |
| 10 | Low Leave Balance | Annual leave balance < 3 days | In-App, Email (weekly) | Employee | `{{employee_name}}`, `{{leave_type}}`, `{{balance_days}}` | 1 retry, 24h apart |
| 11 | Payroll Approved | Payroll run status → approved | Email, In-App | Initiating HR, Finance | `{{run_code}}`, `{{period}}`, `{{total_net}}`, `{{employee_count}}` | 2 retries, 30min apart |
| 12 | Payroll Pending Approval | Payroll run reaches approval stage | Email, In-App | Next approver (Finance/CEO) | `{{run_code}}`, `{{period}}`, `{{total_gross}}`, `{{approval_link}}` | 3 retries, 1h apart |
| 13 | Payslip Generated | PDF payslip created for employee | Email, In-App, Push | Employee | `{{employee_name}}`, `{{period}}`, `{{net_salary}}`, `{{payslip_link}}` | 2 retries, 1h apart |
| 14 | Interview Scheduled | New interview record created | Email, Calendar Invite | Candidate, Interviewers | `{{candidate_name}}`, `{{job_title}}`, `{{date_time}}`, `{{location}}`, `{{meeting_link}}` | 3 retries, 30min apart |
| 15 | Work Anniversary | `joining_date anniversary = TODAY` | Email, In-App | Employee, HR Manager | `{{employee_name}}`, `{{years}}`, `{{joining_date}}` | 1 retry, 4h apart |
| 16 | Birthday | `date_of_birth = TODAY (month+day)` | In-App, Email (opt-in) | Employee, Team | `{{employee_name}}`, `{{first_name}}` | 1 retry, 4h apart |
| 17 | Training Deadline (7-day) | Mandatory training due_date = TODAY + 7 | Email, In-App, SMS | Employee, Manager | `{{employee_name}}`, `{{training_name}}`, `{{due_date}}`, `{{training_link}}` | 2 retries, 2h apart |
| 18 | Training Overdue | Training due_date < TODAY, not completed | Email, SMS | Employee, Manager, HR | `{{employee_name}}`, `{{training_name}}`, `{{days_overdue}}` | Daily retry for 7 days |
| 19 | KPI Review Deadline | Appraisal cycle self-review due in 3 days | Email, In-App | Employee | `{{employee_name}}`, `{{cycle_name}}`, `{{due_date}}`, `{{review_link}}` | 2 retries, 4h apart |
| 20 | Appraisal Pending Manager | Employee submitted self-review | Email, In-App | Manager | `{{employee_name}}`, `{{cycle_name}}`, `{{review_link}}` | 2 retries, 2h apart |
| 21 | High Attrition Risk Alert | Attrition risk score crosses 70% | Email, In-App | HR Manager, HRBP | `{{employee_name}}`, `{{risk_score}}`, `{{risk_tier}}`, `{{top_risk_factor}}`, `{{action_link}}` | 1 retry, 2h apart |
| 22 | Asset Return Overdue | Asset due_return_date < TODAY | Email, In-App | Employee, IT Admin | `{{employee_name}}`, `{{asset_name}}`, `{{asset_tag}}`, `{{due_date}}` | Daily retry for 5 days |
| 23 | Clearance Task Assigned | Offboarding clearance task created | Email, In-App | Assigned department head | `{{employee_name}}`, `{{task}}`, `{{last_working_day}}`, `{{task_link}}` | 3 retries, 1h apart |
| 24 | New Announcement Published | HR publishes company announcement | In-App, Push | All employees (tenant) | `{{title}}`, `{{preview}}`, `{{link}}` | 1 retry, 30min apart |
| 25 | Raise Request Status Update | IT/HR/Admin request status changes | Email, In-App | Requestor Employee | `{{employee_name}}`, `{{request_type}}`, `{{new_status}}`, `{{comment}}` | 2 retries, 1h apart |
| 26 | Document Upload Required | HR flags document missing/expired | Email, In-App | Employee | `{{employee_name}}`, `{{doc_type}}`, `{{deadline}}`, `{{upload_link}}` | 2 retries, daily |
| 27 | Bulk Import Complete | Employee bulk import job finishes | Email, In-App | Initiating HR | `{{total}}`, `{{success}}`, `{{errors}}`, `{{error_report_link}}` | 1 retry, 5min apart |

---

# SECTION 15 — COMPLIANCE CHECKLIST

## 15.1 GDPR Article-by-Article Compliance Map

| GDPR Article | Requirement | HRMS Implementation |
|---|---|---|
| Art. 5 | Lawfulness, fairness, transparency | Privacy notice on employee portal; data processing register in compliance module |
| Art. 6 | Legal basis for processing | HR data processed under Art.6(1)(b) (contract), (c) (legal obligation) for payroll/tax |
| Art. 7 | Conditions for consent | Explicit consent captured for non-essential processing (marketing, alumni); stored in DB |
| Art. 9 | Special category data | Medical data (sick leave certs) encrypted, access-restricted to HR only; minimal retention |
| Art. 12-14 | Transparency & information | Employee portal homepage links to full privacy notice; updated when policies change |
| Art. 15 | Right of access | Employee can download all their data via Self-Service portal within 30 days |
| Art. 16 | Right to rectification | Employee can request data corrections via Raise Request; HR reviews within 5 days |
| Art. 17 | Right to erasure | Subject access request queue in compliance module; automated anonymization pipeline |
| Art. 18 | Right to restriction | HR can flag employee record for processing restriction (locks further changes) |
| Art. 20 | Right to data portability | Employees can export their data in JSON/CSV via Self-Service portal |
| Art. 21 | Right to object | Objection to AI-based decisions (profiling) → HR override workflow in AI module |
| Art. 22 | Automated decision-making | All AI decisions (CV scoring, attrition) have human override; explanation stored in audit |
| Art. 25 | Privacy by design | Tenant isolation, field-level encryption, minimum data collection, RLS |
| Art. 30 | Records of processing | Automated processing activity register maintained in compliance module |
| Art. 32 | Security of processing | AES-256 encryption, TLS 1.3, MFA, RBAC, annual pen-test |
| Art. 33 | Breach notification | Incident response plan triggers 72-hour notification to DPA; Sentry alerts on anomalies |
| Art. 35 | DPIA | DPIA conducted for AI profiling features (attrition, performance prediction) |

## 15.2 Data Retention Policy

| Data Type | Retention Period | Deletion Method |
|---|---|---|
| Employee personal data (active) | Duration of employment | N/A — active record |
| Employee personal data (post-termination) | 7 years (legal obligation) | Anonymize after 7 years |
| Payroll records | 7 years (tax law) | Archive to S3 Glacier → delete at 7y |
| Attendance records | 3 years | Soft delete then hard delete |
| Leave records | 3 years | Soft delete then hard delete |
| Performance reviews | 5 years | Anonymize employee reference after 5y |
| Recruitment data (hired) | 7 years | Anonymize after 7y |
| Recruitment data (rejected) | 1 year (GDPR best practice) | Delete after 1y from rejection |
| Audit logs | 7 years (compliance) | S3 Glacier after 1y, delete at 7y |
| Session tokens | 7 days | Redis TTL auto-expiry |
| TOTP backup codes | Until replaced | Delete on new code generation |
| Exit interview data | 3 years | Anonymize after 3y |
| Medical certificates | 1 year | Secure deletion (DoD 5220.22-M) |
| AI decision records | 3 years | Anonymize employee ref after 3y |

## 15.3 Right to Erasure Implementation

```python
# services/gdpr_service.py
async def process_erasure_request(
    employee_id: str,
    requested_by: str,
    reason: str,
    db: AsyncSession,
) -> dict:
    """
    Process GDPR right-to-erasure request.
    Legal retention obligations take precedence.
    PII is anonymized, not hard-deleted, due to audit requirements.
    """
    # Check if erasure is blocked by legal hold
    active_legal_holds = await _check_legal_holds(employee_id, db)
    if active_legal_holds:
        return {
            "status": "blocked",
            "reason": f"Active legal holds: {active_legal_holds}",
            "review_date": (datetime.now() + timedelta(days=30)).isoformat(),
        }

    # Anonymize PII (replace with hashed pseudonym)
    pseudonym = f"DELETED_USER_{hashlib.sha256(employee_id.encode()).hexdigest()[:12]}"

    await db.execute(text("""
        UPDATE employees SET
            first_name         = :pseudo,
            last_name          = 'USER',
            middle_name        = NULL,
            date_of_birth      = NULL,
            cnic_nid_encrypted = NULL,
            personal_email     = :pseudo_email,
            work_email         = :pseudo_email,
            phone_primary      = NULL,
            phone_secondary    = NULL,
            address_line1      = 'ANONYMIZED',
            address_line2      = NULL,
            city               = NULL,
            postal_code        = NULL,
            emergency_contact_name  = NULL,
            emergency_contact_phone = NULL,
            emergency_contact_email = NULL,
            profile_photo_url  = NULL,
            deleted_at         = NOW(),
            is_active          = FALSE
        WHERE id = :employee_id
    """), {
        "pseudo": pseudonym,
        "pseudo_email": f"{pseudonym}@anonymized.invalid",
        "employee_id": employee_id,
    })

    # Anonymize compensation records
    await db.execute(text("""
        UPDATE employee_compensation SET
            basic_salary_encrypted       = 'ANONYMIZED',
            bank_account_number_encrypted = NULL,
            bank_iban_encrypted           = NULL,
            bank_name                     = NULL
        WHERE employee_id = :employee_id
    """), {"employee_id": employee_id})

    # Delete CV and personal documents from S3
    await _delete_s3_documents(employee_id)

    # Log the erasure in audit (ironically, this record stays for compliance)
    audit_log = AuditLog(
        tenant_id=tenant_id,
        actor_id=requested_by,
        action="gdpr.erasure.completed",
        resource_type="employees",
        resource_id=employee_id,
        new_values={"anonymized": True, "reason": reason},
        severity="critical",
    )
    db.add(audit_log)

    await db.commit()

    return {
        "status": "completed",
        "employee_id": employee_id,
        "pseudonym": pseudonym,
        "completed_at": datetime.now().isoformat(),
        "retained_for_compliance": ["payroll_records", "audit_logs", "tax_records"],
        "message": "PII anonymized. Financial and legal records retained per statutory obligation.",
    }
```

## 15.4 WCAG 2.1 Level AA Implementation

### Technical Requirements

```tsx
// components/ui/FormField.tsx — Accessible form field
import React, { useId } from "react";

interface FormFieldProps {
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: React.ReactElement;
}

export function AccessibleFormField({
  label, required, error, hint, children
}: FormFieldProps) {
  const fieldId = useId();
  const errorId = `${fieldId}-error`;
  const hintId = `${fieldId}-hint`;

  // Build aria-describedby from active descriptors only
  const describedBy = [
    hint && hintId,
    error && errorId,
  ].filter(Boolean).join(" ") || undefined;

  return (
    <div role="group">
      <label
        htmlFor={fieldId}
        className="block text-sm font-medium text-gray-700"
      >
        {label}
        {required && (
          <span aria-label="required" className="text-red-500 ml-1">*</span>
        )}
      </label>

      {hint && (
        <p id={hintId} className="text-xs text-gray-500 mt-0.5">
          {hint}
        </p>
      )}

      {React.cloneElement(children, {
        id: fieldId,
        "aria-required": required,
        "aria-invalid": !!error,
        "aria-describedby": describedBy,
      })}

      {error && (
        <p
          id={errorId}
          role="alert"
          aria-live="assertive"
          className="text-xs text-red-600 mt-1 flex items-center gap-1"
        >
          <span aria-hidden="true">⚠</span>
          {error}
        </p>
      )}
    </div>
  );
}

// components/ui/DataTable.tsx — Accessible table
export function AccessibleDataTable({ columns, data, caption }: TableProps) {
  return (
    <div role="region" aria-label={caption} tabIndex={0}>
      <table>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                scope="col"
                aria-sort={col.sortable ? col.sortDirection || "none" : undefined}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={row.id} tabIndex={0}>
              {columns.map(col => (
                <td key={col.key} data-label={col.label}>
                  {row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Skip navigation link (must be first element in <body>)
export function SkipNavLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded"
    >
      Skip to main content
    </a>
  );
}
```

### Tailwind CSS Accessibility Config
```js
// tailwind.config.js — ensure focus visibility never removed
module.exports = {
  theme: {
    extend: {
      // Custom focus ring that meets WCAG 3:1 contrast
      ringColor: {
        DEFAULT: "#2563EB",  // blue-600
      },
    },
  },
  plugins: [
    // Never allow outline:none or outline:0 without replacement
    function({ addBase }) {
      addBase({
        "*:focus-visible": {
          outline: "2px solid #2563EB",
          outlineOffset: "2px",
        },
        "*:focus:not(:focus-visible)": {
          outline: "none",  // only hide for mouse users
        },
      });
    },
  ],
};
```

---

# SECTION 16 — FUTURE ENHANCEMENTS ROADMAP

## Phase 2 (Months 6–12 post-launch)

| Feature | Business Rationale | Priority |
|---|---|---|
| **Predictive Succession Planning** | Identify high-potential employees and map to critical roles before vacancies occur | P1 |
| **Real-time Salary Benchmarking API** | Integrate with Glassdoor/LinkedIn Salary API to flag below-market compensation automatically | P1 |
| **Employee Wellness Module** | Mental health check-ins, EAP referrals, burnout detection from attendance + overtime patterns | P1 |
| **Advanced Workforce Planning** | Headcount forecasting based on business growth targets + historical hiring velocity | P2 |
| **HR Process Automation (RPA)** | Automate repetitive HR tasks: contract generation, offer letters, onboarding emails with n8n or Zapier | P2 |
| **AI Resume Builder** | Help employees build professional CVs from their HRMS profile data for internal mobility | P2 |
| **360 Feedback Anonymity Guarantee** | Zero-knowledge proof approach to guarantee anonymity of peer reviews | P2 |
| **Multi-language Chatbot (Urdu, Arabic)** | Regional language support for HR chatbot queries | P2 |

## Phase 3 (Months 12–24 post-launch)

| Feature | Business Rationale | Priority |
|---|---|---|
| **Blockchain Credential Verification** | Issue tamper-proof experience certificates on-chain (Polygon/Ethereum L2); verifiable by future employers | P3 |
| **Global Employer of Record (EOR) Integration** | Partner with Deel/Rippling to support contractors in 150+ countries directly from HRMS | P3 |
| **Predictive Hiring Demand Model** | ML model predicts hiring needs 6 months ahead based on project pipeline and attrition forecast | P3 |
| **AI Interview Coach** | Real-time feedback during video interviews (filler words, confidence score, answer quality) | P3 |
| **Compensation Intelligence Engine** | Dynamic salary recommendations based on performance, market data, budget constraints | P3 |
| **Carbon Footprint per Employee** | Track and report employee travel/commute carbon footprint for ESG reporting | P3 |
| **Conversational Onboarding Bot** | WhatsApp/Slack bot that walks new hires through all onboarding tasks step-by-step | P3 |

---

# BONUS 1 — TOOL COMPARISON TABLE

## Custom HRMS vs Commercial HR Software

| Feature | Custom HRMS | SAP SuccessFactors | Workday | BambooHR | Oracle HCM Cloud |
|---|---|---|---|---|---|
| **Implementation Cost** | Medium (dev cost) | Very High ($500K+) | Very High ($300K+) | Low ($50-150/emp/yr) | Very High ($400K+) |
| **Monthly Licensing** | $0 (self-hosted) | $12-25/emp/month | $30-45/emp/month | $8-12/emp/month | $15-35/emp/month |
| **Customization** | ✅ Full control | ⚠️ Limited config | ⚠️ Limited | ❌ Very limited | ⚠️ Limited |
| **AI CV Scoring** | ✅ Custom, bias-aware | ⚠️ Basic | ⚠️ Module add-on | ❌ Not included | ⚠️ Basic |
| **Attrition Prediction** | ✅ Custom + SHAP | ✅ Included | ✅ Included | ❌ Not included | ✅ Included |
| **Local Tax (Pakistan/EOBI)** | ✅ Custom configured | ❌ Requires partner | ❌ Requires partner | ❌ US-focused | ⚠️ Limited |
| **IBFT Bank Export** | ✅ Native | ❌ Custom dev | ❌ Custom dev | ❌ Not supported | ❌ Custom dev |
| **ZKTeco Biometric** | ✅ Direct integration | ⚠️ Third-party | ⚠️ Third-party | ❌ Not supported | ⚠️ Third-party |
| **Multi-tenant (SaaS)** | ✅ Built-in | ✅ Cloud native | ✅ Cloud native | ✅ Cloud native | ✅ Cloud native |
| **Vendor Lock-in** | ✅ None | ❌ High | ❌ High | ❌ Medium | ❌ High |
| **Data Sovereignty** | ✅ Full control | ⚠️ SAP data centers | ⚠️ Workday DC | ⚠️ US servers | ⚠️ Oracle DC |
| **Offline Mobile** | ✅ Custom PWA | ⚠️ Limited | ⚠️ Limited | ❌ Online only | ⚠️ Limited |
| **WhatsApp Chatbot** | ✅ Custom RAG | ⚠️ Connector needed | ❌ Not native | ❌ Not supported | ❌ Not native |
| **Time to Launch** | 4-6 months | 6-18 months | 6-18 months | 2-4 weeks | 9-24 months |
| **Support** | Internal team | 24/7 SAP | 24/7 Workday | Business hours | 24/7 Oracle |

### When to Build vs Buy Decision Framework

```
BUILD custom HRMS when:
  ✅ You have strong local compliance needs (EOBI, SESSI, IBFT, local tax)
  ✅ You need deep integration with local biometric vendors (ZKTeco)
  ✅ You plan to resell/white-label to other companies (multi-tenant SaaS)
  ✅ Data sovereignty is a hard requirement (government, banking sector)
  ✅ Your HR workflows are highly customized and don't fit SAP/Workday templates
  ✅ Scale is 500-5000 employees (custom is cost-competitive in this range)
  ✅ You have an internal engineering team to maintain the system

BUY commercial when:
  ✅ You need to go live in < 60 days with no dev team
  ✅ You operate in multiple countries with standard payroll (US, UK, Europe)
  ✅ Budget is available and TCO of licensing < cost of building + maintaining
  ✅ Scale < 200 employees (BambooHR is a better fit)
  ✅ Your HR team wants a vendor-managed SaaS with zero IT overhead
  ✅ SAP/Oracle integration is required (existing ERP ecosystem)
```
