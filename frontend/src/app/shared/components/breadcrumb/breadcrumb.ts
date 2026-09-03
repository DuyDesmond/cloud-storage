import { Component, input, computed } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { BreadcrumbItem } from '../../../core/file-operations/services/file-operations.service';

@Component({
  selector: 'app-breadcrumb',
  imports: [RouterModule, MatIconModule],
  templateUrl: './breadcrumb.html',
  styleUrl: './breadcrumb.scss',
})
export class Breadcrumb {
  breadcrumbs = input<BreadcrumbItem[]>([]);
  section = input<'drive' | 'shared-with-me' | 'trash' | 'shared'>('drive');
  title = input<string>('');
  description = input<string>('');

  homeLink = computed(() => {
    switch (this.section()) {
      case 'shared-with-me':
        return '/drive/shared-with-me';
      case 'trash':
        return '/trash';
      case 'shared':
        return '/';
      case 'drive':
      default:
        return '/drive/root';
    }
  });

  homeIcon = computed(() => {
    switch (this.section()) {
      case 'shared-with-me':
        return 'group';
      case 'trash':
        return 'delete';
      case 'shared':
        return 'cloud';
      case 'drive':
      default:
        return 'home';
    }
  });
}
