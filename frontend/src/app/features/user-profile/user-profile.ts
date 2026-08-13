import {
  DEFAULT_STORAGE_QUOTA_BYTES,
  FileOperationsService,
} from '../../core/file-operations/services/file-operations.service';
import { Component, inject, signal, computed } from '@angular/core';
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
export class UserProfile {
  private authService = inject(AuthService);
  private router = inject(Router);
  private fileService = inject(FileOperationsService);

  currentUser = this.authService.currentUser;
  userName = computed(() => this.currentUser()?.full_name ?? 'Guest User');
  userEmail = computed(() => this.currentUser()?.email ?? 'No email available');

  // Track active side nav item vs profile state
  activeSideNav = signal<SidePanelNavKey>('');
  isProfileActive = signal<boolean>(true);

  user = signal({
    name: this.userName(),
    email: this.userEmail(),
  });

  usedBytes = signal<number>(0);
  totalBytes = signal<number>(DEFAULT_STORAGE_QUOTA_BYTES);
  usedStorageGB = computed(() => this.usedBytes() / 1024 ** 3);
  totalStorageGB = computed(() => this.totalBytes() / 1024 ** 3);
  storagePercentage = computed(() => {
    const total = this.totalStorageGB();
    if (!total) return 0;
    return Math.min(100, Math.round((this.usedStorageGB() / total) * 100));
  });

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

  fetchStorageUsage(): void {
    this.fileService.getStorageUsage().subscribe({
      next: ({ used_bytes }) => {
        this.usedBytes.set(used_bytes);
        this.totalBytes.set(
          this.currentUser()?.storage_quota ?? DEFAULT_STORAGE_QUOTA_BYTES,
        );
      },
    });
  }

  // Triggered when user clicks the profile icon in app-dashboard-header
  onProfileHeaderClick(): void {
    this.isProfileActive.set(true);
    this.activeSideNav.set(''); // Clear active highlight on side panel links
  }

  // Triggered when user navigates using the side panel or mobile bottom nav
  switchNav(navItem: SidePanelNavKey): void {
    this.activeSideNav.set(navItem);
    this.isProfileActive.set(false);
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
