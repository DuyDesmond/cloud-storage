import { Component, input, output, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { SidePanelNavKey } from '../side-panel/side-panel';

export type NavRoute = 'drive' | 'recent' | 'starred' | 'trash' | '';

@Component({
  selector: 'app-mobile-bottom-nav',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './mobile-bottom-nav.html',
  styleUrls: ['./mobile-bottom-nav.scss'],
})
export class MobileBottomNav {
  private router = inject(Router);
  isProfileActive = signal<boolean>(false);

  currentNav = input<string>('');
  upload = output<void>();
  navChange = output<string>();

  isActive(path: string): boolean {
    if (this.currentNav()) {
      return this.currentNav() === path;
    }
    if (
      path === 'drive' &&
      (this.router.url === '/' || this.router.url.includes('/drive'))
    ) {
      return true;
    }
    return this.router.url.includes(path);
  }

  navigateTo(route: NavRoute): void {
    const routePath = route === 'drive' ? '/drive' : `/${route}`;
    this.router.navigateByUrl(routePath);
  }

  onUploadTrigger(): void {
    this.upload.emit();
  }
}
