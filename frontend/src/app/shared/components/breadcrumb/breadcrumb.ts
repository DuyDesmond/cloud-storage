import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { BreadcrumbItem } from '../../../core/file-operations/services/file-operations.service';

@Component({
  selector: 'app-breadcrumb',
  standalone: true,
  imports: [CommonModule, RouterModule, MatIconModule],
  templateUrl: './breadcrumb.html',
  styleUrls: ['./breadcrumb.scss']
})
export class Breadcrumb {
  @Input() breadcrumbs: BreadcrumbItem[] = [];
  @Input() section: 'drive' | 'shared-with-me' | 'trash' = 'drive';
  @Input() title: string = '';
  @Input() description: string = '';

  get homeLink(): string {
    switch (this.section) {
      case 'shared-with-me': return '/drive/shared-with-me';
      case 'trash': return '/trash';
      case 'drive':
      default: return '/drive/root';
    }
  }

  get homeIcon(): string {
    switch (this.section) {
      case 'shared-with-me': return 'group';
      case 'trash': return 'delete';
      case 'drive':
      default: return 'home';
    }
  }
}
