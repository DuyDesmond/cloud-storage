import { Component, input, output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { SidePanelNavKey, SidePanelNavItem } from '../side-panel/side-panel'; // Adjust path if necessary

@Component({
  selector: 'app-mobile-bottom-nav',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './mobile-bottom-nav.html',
  styleUrls: ['./mobile-bottom-nav.scss'],
})
export class MobileBottomNav {
  private router = inject(Router);
  activeNav = input<SidePanelNavKey>('home');
  navChange = output<SidePanelNavKey>();
  upload = output<void>();

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

  onNavClick(item: SidePanelNavItem): void {
    this.navChange.emit(item.key);
    this.router.navigateByUrl(item.route);
  }
}
