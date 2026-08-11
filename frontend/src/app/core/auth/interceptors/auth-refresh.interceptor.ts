import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { AUTH_ENDPOINTS } from '../endpoints/auth-endpoints';

const REFRESH_URL = AUTH_ENDPOINTS.refresh;

export const authRefreshInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  return next(req).pipe(
    catchError((err: any) => {
      if (
        err &&
        err.status === 401 &&
        !req.headers.has('x-retried') &&
        REFRESH_URL
      ) {
        return auth.refresh().pipe(
          switchMap(() => {
            const retryReq = req.clone({
              headers: req.headers.set('x-retried', '1'),
            });
            return next(retryReq);
          }),
        );
      }

      return throwError(() => err);
    }),
  );
};
