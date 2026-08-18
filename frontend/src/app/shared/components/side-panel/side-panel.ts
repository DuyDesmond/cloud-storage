import {
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { Router } from '@angular/router';
import { DEFAULT_STORAGE_QUOTA_BYTES } from '../../../core/file-operations/services/file-operations.service';

import { StorageStateService } from '../../../core/file-operations/services/storage-state.service';

type SidePanelNavKey = 'home' | 'shared' | 'recent' | 'starred' | 'trash' | '';

export type { SidePanelNavKey };

export interface SidePanelNavItem {
  key: SidePanelNavKey;
  icon: string;
  label: string;
  route: string;
}

@Component({
  selector: 'app-side-panel',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatProgressBarModule],
  host: {
    '[class.is-collapsed]': 'isCollapsed()',
    '[attr.aria-expanded]': '!isCollapsed()',
  },
  templateUrl: './side-panel.html',
  styleUrls: ['./side-panel.scss'],
})
export class SidePanel {
  private router = inject(Router);
  readonly storageState = inject(StorageStateService);

  activeNav = input<SidePanelNavKey>('home');
  navChange = output<SidePanelNavKey>();
  upgrade = output<void>();
  upload = output<void>();

  isCollapsed = signal<boolean>(false);
  collapsedChange = output<boolean>();

  navItems: SidePanelNavItem[] = [
    { key: 'home', icon: 'home', label: 'Home', route: '/drive/root' },
    { key: 'shared', icon: 'group', label: 'Shared with me', route: '/drive/shared-with-me' },
    { key: 'recent', icon: 'schedule', label: 'Recent', route: '/drive/root' },
    { key: 'starred', icon: 'star', label: 'Starred', route: '/drive/root' },
    { key: 'trash', icon: 'delete', label: 'Trash', route: '/trash' },
  ];

  toggleCollapse(): void {
    this.isCollapsed.update((val: boolean) => !val);
  }

  onNavClick(item: SidePanelNavItem): void {
    this.navChange.emit(item.key);
    this.router.navigateByUrl(item.route);
  }
}
