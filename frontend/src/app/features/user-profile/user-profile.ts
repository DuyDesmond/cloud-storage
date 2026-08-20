import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { DashboardHeader } from '../../shared/components/dashboard-header/dashboard-header';
import {
  SidePanel,
  SidePanelNavKey,
} from '../../shared/components/side-panel/side-panel';
import { AuthService } from '@core/auth/services/auth.service';
import { Router } from '@angular/router';
import { MobileBottomNav } from '../../shared/components/mobile-bottom-nav/mobile-bottom-nav';
import { StorageStateService } from '../../core/file-operations/services/storage-state.service';
import { MatSnackBar } from '@angular/material/snack-bar';

export interface StorageCategory {
  name: string;
  icon: string;
  size: string;
  colorClass: string;
}

export interface AccountAction {
  key: ActionKey;
  icon: string;
  title: string;
  description: string;
  isDanger?: boolean;
}

export type ActionKey =
  | 'notifications'
  | 'shared-links'
  | 'logout'
  | 'change-password'
  | 'delete-account';

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatProgressBarModule,
    MatButtonModule,
    DashboardHeader,
    SidePanel,
    MobileBottomNav,
  ],
  templateUrl: './user-profile.html',
  styleUrls: ['./user-profile.scss'],
})
export class UserProfile implements OnInit {
  private authService = inject(AuthService);
  private router = inject(Router);
  private fileService = inject(FileOperationsService);
  private snackBar = inject(MatSnackBar);
  readonly storageState = inject(StorageStateService);

  currentUser = this.authService.currentUser;
  userName = computed(() => this.currentUser()?.full_name ?? 'Guest User');
  userEmail = computed(() => this.currentUser()?.email ?? 'No email available');

  // Track active side nav item vs profile state
  activeSideNav = signal<SidePanelNavKey>('');
  isProfileActive = signal<boolean>(true);

  user = computed(() => ({
    name: this.userName(),
    email: this.userEmail(),
  }));

  storageCategories = signal<StorageCategory[]>([
    {
      name: 'Photos',
      icon: 'image',
      size: '1.8 GB',
      colorClass: 'primary-icon',
    },
    {
      name: 'Documents',
      icon: 'description',
      size: '0.4 GB',
      colorClass: 'secondary-icon',
    },
    {
      name: 'Videos',
      icon: 'movie',
      size: '1.2 GB',
      colorClass: 'tertiary-icon',
    },
    {
      name: 'Other',
      icon: 'more_horiz',
      size: '0.8 GB',
      colorClass: 'outline-icon',
    },
  ]);

  accountActions = signal<AccountAction[]>([
    {
      key: 'notifications',
      icon: 'notifications',
      title: 'Notification Preferences',
      description: 'Manage how you receive alerts',
    },
    {
      key: 'shared-links',
      icon: 'share',
      title: 'Shared Links',
      description: 'Review your active file shares',
    },
    {
      key: 'logout',
      icon: 'logout',
      title: 'Logout',
      description: 'Sign out of your account',
    },
    {
      key: 'change-password',
      icon: 'lock_reset',
      title: 'Change Password',
      description: 'Change your security credentials',
    },
    {
      key: 'delete-account',
      icon: 'delete',
      title: 'Delete Account',
      description: 'Permanently remove your data',
      isDanger: true,
    },
  ]);

  ngOnInit(): void {
    this.storageState.refreshStorageUsage();
  }

  // Triggered when user clicks the profile icon in app-dashboard-header
  onProfileHeaderClick(): void {
    this.isProfileActive.set(true);
    this.activeSideNav.set(''); // Clear active highlight on side panel links
  }

  onUploadTrigger(): void {
    console.log('Upload action triggered');
  }

  onActionClick(action: AccountAction): void {
    switch (action.key) {
      case 'logout':
        this.handleLogout();
        break;
      case 'change-password':
        this.handleChangePassword();
        break;
      case 'delete-account':
        this.handleDeleteAccount();
        break;
      default:
        console.log('Action clicked:', action.title);
        break;
    }
  }

  private handleLogout(): void {
    this.authService.logout().subscribe({
      next: () => {
        this.router.navigate(['/login']);
      },
      error: (err) => {
        console.error('Logout failed:', err);
        this.router.navigate(['/login']); // Fallback redirect
      },
    });
  }

  private handleChangePassword(): void {
    const currentPass = window.prompt('Enter your current password:');
    if (!currentPass) return;

    const newPass = window.prompt('Enter your new passwo3 rd (min 8 chars):');
    if (!newPass) return;

    this.authService.changePassword(currentPass, newPass).subscribe({
      next: (res) => {
        alert(res.message);
      },
      error: (err) => {
        alert(err.error?.detail ?? 'Failed to change password');
      },
    });
  }

  private handleDeleteAccount(): void {
    const confirmed = window.confirm(
      'Are you sure you want to permanently delete your account? This action cannot be undone.',
    );

    if (confirmed) {
      this.authService.deleteAccount().subscribe({
        next: (res) => {
          alert(res.message);
          this.router.navigate(['/login']);
        },
        error: (err) => {
          alert(err.error?.detail ?? 'Failed to delete account');
        },
      });
    }
  }
}
