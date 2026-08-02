import { environment } from '../../../../environments/environment';

export const AUTH_ENDPOINTS = {
  login: `${environment.apiUrl}/api/v1/auth/login`,
  register: `${environment.apiUrl}/api/v1/auth/register`,
  profile: `${environment.apiUrl}/api/v1/auth/me`,
  refresh: `${environment.apiUrl}/api/v1/auth/refresh`,
  logout: `${environment.apiUrl}/api/v1/auth/logout`,
  deleteAccount: `${environment.apiUrl}/api/v1/auth/me`,
  changePassword: `${environment.apiUrl}/api/v1/auth/change-password`,
  forgotPassword: `${environment.apiUrl}/api/v1/auth/forgot-password`,
  resetPassword: `${environment.apiUrl}/api/v1/auth/reset-password`,
} as const;
