import { Component, input, output, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { DriveItem } from './drive-item.model';

@Component({
  selector: 'app-drive-item-card',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatMenuModule],
  templateUrl: './drive-item-card.html',
  styleUrls: ['./drive-item-card.scss'],
})
export class DriveItemCard {
  item = input.required<DriveItem>();
  isTrashView = input<boolean>();

  // Outputs for parent drive component actions
  open = output<DriveItem>();
  download = output<DriveItem>();
  share = output<DriveItem>();
  trash = output<DriveItem>();
  restore = output<DriveItem>();
  permanentDelete = output<DriveItem>();

  // Dynamic formatting based on DB schema fields
  displayMeta = computed(() => {
    const item = this.item();
    if (item.itemType === 'folder') {
      return `${item.itemsCount ?? 0} items`;
    }
    return this.formatBytes(item.sizeBytes);
  });

  iconName = computed(() => {
    const item = this.item();
    if (item.itemType === 'folder') return 'folder';

    const mime = item.mimeType ?? '';
    if (mime.startsWith('image/')) return 'image';
    if (mime.startsWith('video/')) return 'movie';
    if (mime.includes('pdf')) return 'picture_as_pdf';
    return 'description';
  });

  onCardClick(): void {
    this.open.emit(this.item());
  }

  onDownload(event: MouseEvent): void {
    event.stopPropagation();
    this.download.emit(this.item());
  }

  onShare(event: MouseEvent): void {
    event.stopPropagation();
    this.share.emit(this.item());
  }

  onTrash(event: MouseEvent): void {
    event.stopPropagation();
    this.trash.emit(this.item());
  }

  onRestore(event: MouseEvent): void {
    event.stopPropagation();
    this.restore.emit(this.item());
  }

  onPermanentDelete(event: MouseEvent): void {
    event.stopPropagation();
    this.permanentDelete.emit(this.item());
  }

  private formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
}
