import { Routes } from '@angular/router';
import { Login } from './features/auth/components/login/login';
import { Register } from './features/auth/components/register/register';
import { Landing } from './features/landing/landing';
import { Drive } from './features/drive/drive';
import { UserProfile } from './features/user-profile/user-profile';
import { authGuard } from './core/auth/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'landing', pathMatch: 'full' },
  { path: 'landing', component: Landing },
  { path: 'login', component: Login },
  { path: 'register', component: Register },
  { path: 'drive', component: Drive, canActivate: [authGuard] },
  { path: 'profile', component: UserProfile, canActivate: [authGuard] },
  { path: '**', redirectTo: 'landing' },
];
