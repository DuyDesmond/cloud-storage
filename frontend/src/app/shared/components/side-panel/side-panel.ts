import {
  Component,
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
  usedStorage = input(0);
  totalStorage = input(1);
  activeNav = input<SidePanelNavKey>('home');
  navChange = output<SidePanelNavKey>();
  upgrade = output<void>();
  upload = output<void>();

  isCollapsed = signal<boolean>(false);
  collapsedChange = output<boolean>();

  navItems: SidePanelNavItem[] = [
    { key: 'home', icon: 'home', label: 'Home', route: '/drive' },
    { key: 'recent', icon: 'schedule', label: 'Recent', route: '/drive' },
    { key: 'starred', icon: 'star', label: 'Starred', route: '/drive' },
    { key: 'trash', icon: 'delete', label: 'Trash', route: '/drive' },
  ];

  storagePercentage(): number {
    return Math.round((this.usedStorage() / this.totalStorage()) * 100);
  }

  toggleCollapse(): void {
    this.isCollapsed.update((val: boolean) => !val);
  }

  onNavClick(item: SidePanelNavItem): void {
    this.navChange.emit(item.key);
    this.router.navigateByUrl(item.route);
  }
}
