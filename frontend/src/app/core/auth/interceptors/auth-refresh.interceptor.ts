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
import { TokenRefreshStateService } from '../services/token-refresh-state.service';

const REFRESH_URL = AUTH_ENDPOINTS.refresh;

export const authRefreshInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const state = inject(TokenRefreshStateService);

  return next(req).pipe(
    catchError((err: any) => {
      // 1. CRITICAL FIX: Ignore 401s coming directly from the refresh endpoint itself
      const isRefreshRequest = req.url.includes(REFRESH_URL);

      if (
        err?.status === 401 &&
        !isRefreshRequest &&
        !req.headers.has('x-retried')
      ) {
        return handle401Error(req, next, auth, state);
      }

      // If the refresh call ITSELF failed with 401, logout and break the loop
      if (err?.status === 401 && isRefreshRequest) {
        state.isRefreshing = false;
        state.refreshTokenSubject.next(false);
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
  state: TokenRefreshStateService
) {
  if (!state.isRefreshing) {
    state.isRefreshing = true;
    state.refreshTokenSubject.next(null);

    return auth.refresh().pipe(
      switchMap(() => {
        state.isRefreshing = false;
        state.refreshTokenSubject.next(true);

        const retryReq = req.clone({
          headers: req.headers.set('x-retried', '1'),
        });
        return next(retryReq);
      }),
      catchError((refreshErr) => {
        state.isRefreshing = false;
        state.refreshTokenSubject.next(false);
        auth.logout();
        return throwError(() => refreshErr);
      }),
    );
  } else {
    // If a refresh is ALREADY in progress, queue subsequent 401 requests until it finishes
    return state.refreshTokenSubject.pipe(
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
