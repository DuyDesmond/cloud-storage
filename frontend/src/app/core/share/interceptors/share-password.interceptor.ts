import {
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
  HttpErrorResponse,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { MatDialog } from '@angular/material/dialog';
import {
  catchError,
  switchMap,
  throwError,
  of,
  Observable,
  filter,
} from 'rxjs';
import { SharePasswordService } from '../services/share-password.service';
import { PasswordPromptComponent } from '../../../shared/components/password-prompt/password-prompt';
import { BehaviorSubject, take } from 'rxjs';

let isPrompting = false;
const passwordSubject = new BehaviorSubject<string | null>(null);

export const sharePasswordInterceptor: HttpInterceptorFn = (req, next) => {
  const passwordService = inject(SharePasswordService);
  const dialog = inject(MatDialog);

  // Attach current password if it exists
  const password = passwordService.getPassword();
  let modifiedReq = req;

  if (password && req.url.includes(`${environment.apiStr}/storage`)) {
    modifiedReq = req.clone({
      setHeaders: { 'X-Share-Password': password },
    });
  }

  return next(modifiedReq).pipe(
    catchError((err: HttpErrorResponse) => {
      // check if error is related to share password
      if (
        err.status === 401 &&
        err.error?.detail &&
        (err.error.detail === 'PASSWORD_REQUIRED' ||
          err.error.detail === 'INVALID_PASSWORD')
      ) {
        // if INVALID_PASSWORD, clear the wrong one
        if (err.error.detail === 'INVALID_PASSWORD') {
          passwordService.clearPassword();
        }

        if (!isPrompting) {
          isPrompting = true;
          passwordSubject.next(null);

          return promptForPassword(dialog).pipe(
            switchMap((newPassword) => {
              isPrompting = false;
              if (!newPassword) {
                passwordSubject.error(err);
                return throwError(() => err);
              }
              passwordService.setPassword(newPassword);
              passwordSubject.next(newPassword);

              const retryReq = req.clone({
                setHeaders: { 'X-Share-Password': newPassword },
              });
              return next(retryReq);
            }),
            catchError((promptErr) => {
              isPrompting = false;
              return throwError(() => promptErr);
            }),
          );
        } else {
          return passwordSubject.pipe(
            filter((token) => token !== null),
            take(1),
            switchMap((newPassword) => {
              const retryReq = req.clone({
                setHeaders: { 'X-Share-Password': newPassword as string },
              });
              return next(retryReq);
            }),
            catchError(() => throwError(() => err)),
          );
        }
      }

      return throwError(() => err);
    }),
  );
};

function promptForPassword(dialog: MatDialog): Observable<string | null> {
  const dialogRef = dialog.open(PasswordPromptComponent, {
    width: '400px',
    disableClose: true,
  });

  return dialogRef.afterClosed();
}
