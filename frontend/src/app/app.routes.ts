import { Routes } from '@angular/router';
import { Login } from './features/auth/components/login/login';
import { Register } from './features/auth/components/register/register';
import { Landing } from './features/landing/landing';
import { Drive } from './features/drive/drive';
import { UserProfile } from './features/user-profile/user-profile';
import { authGuard } from './core/auth/guards/auth.guard';
import { Trash } from './features/trash/trash';
import { SharedWithMe } from './features/shared-with-me/shared-with-me';

export const routes: Routes = [
  { path: '', redirectTo: 'landing', pathMatch: 'full' },
  { path: 'landing', component: Landing },
  { path: 'login', component: Login },
  { path: 'register', component: Register },
  { path: 'drive', redirectTo: 'drive/root', pathMatch: 'full' },
  { path: 'drive/root', component: Drive, canActivate: [authGuard] },
  { path: 'drive/root/folder/:id', component: Drive, canActivate: [authGuard] },
  { path: 'drive/shared-with-me', component: SharedWithMe, canActivate: [authGuard] },
  { path: 'drive/shared-with-me/folder/:id', component: SharedWithMe, canActivate: [authGuard] },
  { path: 'profile', component: UserProfile, canActivate: [authGuard] },
  { path: 'trash', component: Trash, canActivate: [authGuard] },
  { path: '**', redirectTo: 'landing' },
];
