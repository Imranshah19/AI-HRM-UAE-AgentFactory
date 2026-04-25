export interface Permission {
  module_name: string;
  action: string;
}

export interface Role {
  id: string;
  name: string;
  is_system_role: boolean;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  avatar_url: string | null;
  tenant_id: string;
  tenant_slug?: string;
  is_superadmin: boolean;
  roles: Role[];
  permissions: Permission[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}
