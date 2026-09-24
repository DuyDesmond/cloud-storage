import { Component, input, computed, output, signal } from '@angular/core';
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

  droppedOnCrumb = output<{
    sourceId: string;
    sourceType: 'file' | 'folder';
    targetFolderId: string | null;
  }>();

  dragTargetCrumbId = signal<string | null>(null);
  isDragTargetRoot = signal(false);

  onDragOverCrumb(event: DragEvent, crumbId: string | null): void {
    const types = event.dataTransfer?.types;
    if (types && types.includes('application/x-nephos-move-item')) {
      event.preventDefault();
      event.stopPropagation();
      if (crumbId) {
        this.dragTargetCrumbId.set(crumbId);
      } else {
        this.isDragTargetRoot.set(true);
      }
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'move';
      }
    }
  }

  onDragLeaveCrumb(event: DragEvent, crumbId: string | null): void {
    event.preventDefault();
    event.stopPropagation();
    if (crumbId) {
      if (this.dragTargetCrumbId() === crumbId) {
        this.dragTargetCrumbId.set(null);
      }
    } else {
      this.isDragTargetRoot.set(false);
    }
  }

  onDropCrumb(event: DragEvent, crumbId: string | null): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragTargetCrumbId.set(null);
    this.isDragTargetRoot.set(false);

    const dataString = event.dataTransfer?.getData(
      'application/x-nephos-move-item',
    );
    if (dataString) {
      try {
        const data = JSON.parse(dataString);
        if (data.id === crumbId) return; // Cannot drop folder onto itself
        this.droppedOnCrumb.emit({
          sourceId: data.id,
          sourceType: data.type,
          targetFolderId: crumbId,
        });
      } catch (e) {
        console.error('Failed to parse dropped item', e);
      }
    }
  }
}
