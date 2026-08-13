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

type SidePanelNavKey = 'home' | 'recent' | 'starred' | 'trash' | '';

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
  activeNav = input<SidePanelNavKey>('home');
  navChange = output<SidePanelNavKey>();
  upgrade = output<void>();
  upload = output<void>();

  usedBytes = input<number>(0);
  totalBytes = input<number>(DEFAULT_STORAGE_QUOTA_BYTES);
  usedStorageGB = computed(() => this.usedBytes() / 1024 ** 3);
  totalStorageGB = computed(() => this.totalBytes() / 1024 ** 3);

  isCollapsed = signal<boolean>(false);
  collapsedChange = output<boolean>();

  isLoading = signal<boolean>(true);

  ngOnChanges() {
    if (this.usedBytes() && this.totalBytes()) {
      this.isLoading.set(false);
    }
  }

  navItems: SidePanelNavItem[] = [
    { key: 'home', icon: 'home', label: 'Home', route: '/drive' },
    { key: 'recent', icon: 'schedule', label: 'Recent', route: '/drive' },
    { key: 'starred', icon: 'star', label: 'Starred', route: '/drive' },
    { key: 'trash', icon: 'delete', label: 'Trash', route: '/trash' },
  ];

  storagePercentage(): number {
    const total = this.totalStorageGB();
    if (!total) return 0;
    return Math.min(100, Math.round((this.usedStorageGB() / total) * 100));
  }

  toggleCollapse(): void {
    this.isCollapsed.update((val: boolean) => !val);
  }

  onNavClick(item: SidePanelNavItem): void {
    this.navChange.emit(item.key);
    this.router.navigateByUrl(item.route);
  }
}
