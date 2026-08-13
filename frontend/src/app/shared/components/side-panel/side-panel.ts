import {
  Component,
  computed,
  EventEmitter,
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
import { FileOperationsService } from '../../../core/file-operations/services/file-operations.service';

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
  private fileService = inject(FileOperationsService);
  activeNav = input<SidePanelNavKey>('home');
  navChange = output<SidePanelNavKey>();
  upgrade = output<void>();
  upload = output<void>();

  usedBytes = input<number>(0);
  totalBytes = input<number>(20 * 1024 ** 3);
  usedStorageGB = computed(() => this.usedBytes() / 1024 ** 3);
  totalStorageGB = computed(() => this.totalBytes() / 1024 ** 3);

  isCollapsed = signal<boolean>(false);
  collapsedChange = output<boolean>();

  navItems: SidePanelNavItem[] = [
    { key: 'home', icon: 'home', label: 'Home', route: '/drive' },
    { key: 'recent', icon: 'schedule', label: 'Recent', route: '/drive' },
    { key: 'starred', icon: 'star', label: 'Starred', route: '/drive' },
    { key: 'trash', icon: 'delete', label: 'Trash', route: '/trash' },
  ];

  storagePercentage(): number {
    return Math.round((this.usedStorageGB() / this.totalStorageGB()) * 100);
  }

  toggleCollapse(): void {
    this.isCollapsed.update((val: boolean) => !val);
  }

  onNavClick(item: SidePanelNavItem): void {
    this.navChange.emit(item.key);
    this.router.navigateByUrl(item.route);
  }

  // fetchStorageUsage(): void {
  //   this.fileService.getStorageUsage().subscribe({
  //     next: ({ used_bytes, total_bytes }) => {
  //       this.usedBytes.set(used_bytes);
  //       this.totalBytes.set(total_bytes);
  //     },
  //   });
  // }
}
