import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { AUTH_ENDPOINTS } from '../endpoints/auth-endpoints';

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  created_at: string;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  currentUser = signal<User | null>(null);

  private http = inject(HttpClient);

  login(email: string, password: string): Observable<User> {
    return this.http
      .post<User>(
        `${AUTH_ENDPOINTS.login}`,
        { email, password },
        { withCredentials: true },
      )
      .pipe(tap((user) => this.currentUser.set(user)));
  }

  register(
    username: string,
    email: string,
    password: string,
  ): Observable<User> {
    return this.http
      .post<User>(
        `${AUTH_ENDPOINTS.register}`,
        { email, password, full_name: username },
        { withCredentials: true },
      )
      .pipe(tap((user) => this.currentUser.set(user)));
  }

  getProfile(): Observable<User> {
    return this.http
      .get<User>(`${AUTH_ENDPOINTS.profile}`, { withCredentials: true })
      .pipe(
        tap((user) => this.currentUser.set(user)),
        catchError((err) => {
          this.currentUser.set(null);
          throw err;
        }),
      );
  }

  refresh(): Observable<User> {
    return this.http
      .post<User>(`${AUTH_ENDPOINTS.refresh}`, {}, { withCredentials: true })
      .pipe(tap((user) => this.currentUser.set(user)));
  }

  logout(): Observable<{ message: string }> {
    return this.http
      .post<{ message: string }>(
        `${AUTH_ENDPOINTS.logout}`,
        {},
        { withCredentials: true },
      )
      .pipe(tap(() => this.currentUser.set(null)));
  }

  deleteAccount(): Observable<{ message: string }> {
    return this.http
      .delete<{ message: string }>(`${AUTH_ENDPOINTS.deleteAccount}`, {
        withCredentials: true,
      })
      .pipe(tap(() => this.currentUser.set(null)));
  }

  changePassword(
    current: string,
    newPassword: string,
  ): Observable<{ message: string }> {
    return this.http.put<{ message: string }>(
      `${AUTH_ENDPOINTS.changePassword}`,
      { current_password: current, new_password: newPassword },
      { withCredentials: true },
    );
  }

  forgotPassword(email: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${AUTH_ENDPOINTS.forgotPassword}`,
      { email },
    );
  }

  resetPassword(
    token: string,
    newPassword: string,
  ): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${AUTH_ENDPOINTS.resetPassword}`,
      { token, new_password: newPassword },
    );
  }
}
