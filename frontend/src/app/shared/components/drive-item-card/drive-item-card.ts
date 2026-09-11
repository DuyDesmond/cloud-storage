import { Component, input, output, computed, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { DriveItem, DriveFileItem } from './drive-item.model';
import { FileSizePipe } from '../../pipes/file-size.pipe';
import { MimeIconPipe } from '../../pipes/mime-icon.pipe';

@Component({
  selector: 'app-drive-item-card',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    DatePipe,
    FileSizePipe,
    MimeIconPipe,
  ],
  templateUrl: './drive-item-card.html',
  styleUrl: './drive-item-card.scss',
})
export class DriveItemCard {
  item = input.required<DriveItem>();
  isTrashView = input<boolean>();
  readonly = input<boolean>(false);

  // Outputs for parent drive component actions
  open = output<DriveItem>();
  download = output<DriveItem>();
  share = output<DriveItem>();
  trash = output<DriveItem>();
  restore = output<DriveItem>();
  permanentDelete = output<DriveItem>();
  moveToFolder = output<{
    sourceId: string;
    sourceType: 'file' | 'folder';
    targetFolderId: string;
  }>();

  isDragTarget = signal(false);

  fileItem = computed(() => {
    const i = this.item();
    return i.itemType === 'file' ? (i as DriveFileItem) : null;
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

  onDragStart(event: DragEvent): void {
    if (this.readonly()) return;
    const itemData = { id: this.item().id, type: this.item().itemType };
    event.dataTransfer?.setData(
      'application/x-nephos-move-item',
      JSON.stringify(itemData),
    );
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
    }
  }

  onDragOver(event: DragEvent): void {
    if (this.readonly() || this.item().itemType !== 'folder') return;
    const types = event.dataTransfer?.types;
    if (types && types.includes('application/x-nephos-move-item')) {
      event.preventDefault();
      event.stopPropagation();
      this.isDragTarget.set(true);
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'move';
      }
    }
  }

  onDragLeave(event: DragEvent): void {
    if (this.readonly() || this.item().itemType !== 'folder') return;
    event.preventDefault();
    event.stopPropagation();
    this.isDragTarget.set(false);
  }

  onDrop(event: DragEvent): void {
    if (this.readonly() || this.item().itemType !== 'folder') return;
    event.preventDefault();
    event.stopPropagation();
    this.isDragTarget.set(false);

    const dataString = event.dataTransfer?.getData(
      'application/x-nephos-move-item',
    );
    if (dataString) {
      try {
        const data = JSON.parse(dataString);
        if (data.id === this.item().id) return;

        this.moveToFolder.emit({
          sourceId: data.id,
          sourceType: data.type,
          targetFolderId: this.item().id,
        });
      } catch (e) {
        console.error('Failed to parse dropped item', e);
      }
    }
  }
}
