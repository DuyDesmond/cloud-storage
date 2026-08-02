import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideAppInitializer,
  inject,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './core/auth/services/auth.service';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { authRefreshInterceptor } from './core/auth/interceptors/auth-refresh.interceptor';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptorsFromDi()),
    provideAppInitializer(() =>
      firstValueFrom(inject(AuthService).getProfile()).catch(() => null),
    ),
  ],
};
