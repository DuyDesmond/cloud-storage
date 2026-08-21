import { environment } from '../../../../environments/environment';

export const AUTH_ENDPOINTS = {
  login: `${environment.apiUrl}${environment.apiStr}/auth/login`,
  register: `${environment.apiUrl}${environment.apiStr}/auth/register`,
  profile: `${environment.apiUrl}${environment.apiStr}/auth/me`,
  refresh: `${environment.apiUrl}${environment.apiStr}/auth/refresh`,
  logout: `${environment.apiUrl}${environment.apiStr}/auth/logout`,
  deleteAccount: `${environment.apiUrl}${environment.apiStr}/auth/me`,
  changePassword: `${environment.apiUrl}${environment.apiStr}/auth/change-password`,
  forgotPassword: `${environment.apiUrl}${environment.apiStr}/auth/forgot-password`,
  resetPassword: `${environment.apiUrl}${environment.apiStr}/auth/reset-password`,
} as const;
