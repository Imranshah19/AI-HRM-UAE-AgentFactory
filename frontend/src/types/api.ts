export interface ApiResponse<T> {
  data: T;
  success?: boolean;
  message?: string;
}

export interface PaginatedResponse<T> {
  // Backend format (FastAPI pagination)
  results:   T[];
  count:     number;
  page:      number;
  page_size: number;
  // Legacy aliases
  items?:    T[];
  total?:    number;
  pages?:    number;
}

export interface ApiErrorDetail {
  msg: string;
  type: string;
  loc?: string[];
}

export interface ApiError {
  detail: string | ApiErrorDetail[];
  status_code?: number;
}
