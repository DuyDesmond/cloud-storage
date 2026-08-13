import {
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { inject } from '@angular/core';
import {
  BehaviorSubject,
  catchError,
  filter,
  switchMap,
  take,
  throwError,
} from 'rxjs';
import { AuthService } from '../services/auth.service';
import { AUTH_ENDPOINTS } from '../endpoints/auth-endpoints';

const REFRESH_URL = AUTH_ENDPOINTS.refresh;

// State tracking for concurrent 401 handling
let isRefreshing = false;
const refreshTokenSubject = new BehaviorSubject<boolean | null>(null);

export const authRefreshInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  return next(req).pipe(
    catchError((err: any) => {
      // 1. CRITICAL FIX: Ignore 401s coming directly from the refresh endpoint itself
      const isRefreshRequest = req.url.includes(REFRESH_URL);

      if (
        err?.status === 401 &&
        !isRefreshRequest &&
        !req.headers.has('x-retried')
      ) {
        return handle401Error(req, next, auth);
      }

      // If the refresh call ITSELF failed with 401, logout and break the loop
      if (err?.status === 401 && isRefreshRequest) {
        isRefreshing = false;
        refreshTokenSubject.next(false);
        auth.logout(); // Redirect to login cleanly instead of looping
      }

      return throwError(() => err);
    }),
  );
};

function handle401Error(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  auth: AuthService,
) {
  if (!isRefreshing) {
    isRefreshing = true;
    refreshTokenSubject.next(null);

    return auth.refresh().pipe(
      switchMap(() => {
        isRefreshing = false;
        refreshTokenSubject.next(true);

        const retryReq = req.clone({
          headers: req.headers.set('x-retried', '1'),
        });
        return next(retryReq);
      }),
      catchError((refreshErr) => {
        isRefreshing = false;
        refreshTokenSubject.next(false);
        auth.logout();
        return throwError(() => refreshErr);
      }),
    );
  } else {
    // If a refresh is ALREADY in progress, queue subsequent 401 requests until it finishes
    return refreshTokenSubject.pipe(
      filter((result) => result !== null),
      take(1),
      switchMap((success) => {
        if (success) {
          const retryReq = req.clone({
            headers: req.headers.set('x-retried', '1'),
          });
          return next(retryReq);
        }
        return throwError(() => new Error('Session expired'));
      }),
    );
  }
}
