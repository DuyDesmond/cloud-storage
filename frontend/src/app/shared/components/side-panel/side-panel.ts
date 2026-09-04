import {
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterModule } from '@angular/router';
import { DEFAULT_STORAGE_QUOTA_BYTES } from '../../../core/file-operations/services/file-operations.service';

import { StorageStateService } from '../../../core/file-operations/services/storage-state.service';
import { FileSizePipe } from '../../pipes/file-size.pipe';

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
  imports: [
    RouterModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
    FileSizePipe,
  ],
  host: {
    '[class.is-collapsed]': 'isCollapsed()',
    '[attr.aria-expanded]': '!isCollapsed()',
  },
  templateUrl: './side-panel.html',
  styleUrl: './side-panel.scss',
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
    {
      key: 'shared',
      icon: 'group',
      label: 'Shared with me',
      route: '/drive/shared-with-me',
    },
    { key: 'starred', icon: 'star', label: 'Favorites', route: '/drive/root' },
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
