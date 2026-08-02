import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { map, catchError, of } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  // If we already have a user in memory, allow immediately
  if (auth.currentUser()) return true;

  // Otherwise attempt to hydrate profile; redirect to /login on failure
  return auth.getProfile().pipe(
    map(() => true),
    catchError(() => of(router.parseUrl('/login'))),
  );
};
