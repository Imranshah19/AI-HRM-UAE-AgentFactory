// AI-HRMS — Asset Management TypeScript types

export type AssetCategory =
  | 'laptop' | 'desktop' | 'mobile' | 'tablet' | 'monitor'
  | 'keyboard' | 'mouse' | 'headset' | 'sim_card' | 'access_card'
  | 'vehicle' | 'furniture' | 'other';

export type AssetStatus    = 'available' | 'assigned' | 'maintenance' | 'retired' | 'lost' | 'disposed';
export type AssetCondition = 'excellent' | 'good' | 'fair' | 'poor' | 'damaged';

export interface EmployeeMinimal {
  id:            string;
  employee_code: string;
  full_name:     string;
  department?:   string | null;
  designation?:  string | null;
}

export interface Asset {
  id:              string;
  asset_tag:       string;
  name:            string;
  category:        AssetCategory;
  brand:           string | null;
  model:           string | null;
  serial_number:   string | null;
  specifications:  Record<string, unknown> | null;
  purchase_date:   string | null;
  purchase_cost:   number | null;
  current_value:   number | null;
  currency:        string;
  vendor:          string | null;
  warranty_expiry: string | null;
  condition:       AssetCondition;
  status:          AssetStatus;
  location:        string | null;
  notes:           string | null;
  current_employee_id: string | null;
  current_employee:    EmployeeMinimal | null;
  assigned_since:  string | null;
  is_active:       boolean;
  created_at:      string;
  updated_at:      string;
}

export interface AssetListItem {
  id:          string;
  asset_tag:   string;
  name:        string;
  category:    AssetCategory;
  brand:       string | null;
  condition:   AssetCondition;
  status:      AssetStatus;
  current_employee: EmployeeMinimal | null;
  assigned_since:   string | null;
  warranty_expiry:  string | null;
}

export interface AssetAssignment {
  id:                      string;
  asset_id:                string;
  employee_id:             string;
  employee?:               EmployeeMinimal | null;
  assigned_at:             string;
  condition_at_assignment: AssetCondition;
  assignment_notes:        string | null;
  returned_at:             string | null;
  condition_at_return:     AssetCondition | null;
  return_notes:            string | null;
  is_damaged:              boolean;
  damage_description:      string | null;
  damage_cost:             number | null;
  created_at:              string;
  updated_at:              string;
}

export interface AssetCreate {
  asset_tag?:       string | null;
  name:             string;
  category:         AssetCategory;
  brand?:           string | null;
  model?:           string | null;
  serial_number?:   string | null;
  purchase_date?:   string | null;
  purchase_cost?:   number | null;
  current_value?:   number | null;
  currency?:        string;
  vendor?:          string | null;
  warranty_expiry?: string | null;
  condition?:       AssetCondition;
  location?:        string | null;
  notes?:           string | null;
}

export interface AssetUpdate {
  name?:           string;
  brand?:          string | null;
  model?:          string | null;
  serial_number?:  string | null;
  purchase_cost?:  number | null;
  current_value?:  number | null;
  warranty_expiry?: string | null;
  condition?:      AssetCondition;
  status?:         AssetStatus;
  location?:       string | null;
  notes?:          string | null;
}

export interface AssetAssignmentRequest {
  employee_id:             string;
  condition_at_assignment: AssetCondition;
  notes?:                  string | null;
}

export interface AssetReturnRequest {
  condition_at_return: AssetCondition;
  notes?:              string | null;
  is_damaged?:         boolean;
  damage_description?: string | null;
  damage_cost?:        number | null;
}

export interface AssetListResponse {
  count:   number;
  results: AssetListItem[];
}

export interface AssetFilterParams {
  category?:  AssetCategory;
  status?:    AssetStatus;
  assigned?:  boolean;
  search?:    string;
  page?:      number;
  page_size?: number;
}
