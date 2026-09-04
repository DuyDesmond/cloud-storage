import { Component, inject, signal } from '@angular/core';

import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import {
  traverseDataTransferItems,
  buildFolderTreeFromFiles,
  TraversedFileItem,
  TraversedFolderItem,
} from '../../shared/utils/folder-traversal';

export interface UploadDialogResult {
  action: 'upload' | 'create-folder';
  files?: File[];
  traversedFolders?: TraversedFolderItem[];
  folderName?: string;
}

@Component({
  selector: 'app-upload-dialog',
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    FormsModule,
  ],
  templateUrl: './upload-dialog.html',
  styleUrl: './upload-dialog.scss',
})
export class UploadDialog {
  private dialogRef = inject(MatDialogRef<UploadDialog>);

  isDragging = signal(false);
  selectedFiles = signal<File[]>([]);
  traversedFolders = signal<TraversedFolderItem[]>([]);
  isCreatingFolder = signal(false);
  newFolderName = signal('');

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);
  }

  async onDrop(event: DragEvent): Promise<void> {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);

    if (event.dataTransfer?.items?.length) {
      const result = await traverseDataTransferItems(event.dataTransfer.items);
      if (result.folders.length) {
        this.traversedFolders.update((f) => [...f, ...result.folders]);
      }
      if (result.files.length) {
        const droppedFiles = result.files.map((tf) => tf.file);
        this.selectedFiles.update((files) => [...files, ...droppedFiles]);
      }
    } else if (event.dataTransfer?.files?.length) {
      const droppedFiles = Array.from(event.dataTransfer.files);
      this.selectedFiles.update((files) => [...files, ...droppedFiles]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      const files = Array.from(input.files);
      const isFolderInput = input.hasAttribute('webkitdirectory');

      if (isFolderInput) {
        const result = buildFolderTreeFromFiles(files);
        if (result.folders.length > 0) {
          this.traversedFolders.update((existing) => [
            ...existing,
            ...result.folders,
          ]);
        }
        if (result.files.length > 0) {
          this.selectedFiles.update((existing) => [
            ...existing,
            ...result.files,
          ]);
        }
      } else {
        this.selectedFiles.update((existing) => [...existing, ...files]);
      }
    }
    input.value = '';
  }

  removeFile(index: number): void {
    this.selectedFiles.update((files) => files.filter((_, i) => i !== index));
  }

  removeFolder(index: number): void {
    this.traversedFolders.update((folders) =>
      folders.filter((_, i) => i !== index),
    );
  }

  toggleFolderInput(): void {
    this.isCreatingFolder.update((val) => !val);
    this.newFolderName.set('');
  }

  submitFolder(): void {
    if (this.newFolderName().trim()) {
      this.dialogRef.close({
        action: 'create-folder',
        folderName: this.newFolderName().trim(),
      });
    }
  }

  confirmUpload(): void {
    if (this.selectedFiles().length > 0 || this.traversedFolders().length > 0) {
      this.dialogRef.close({
        action: 'upload',
        files: this.selectedFiles(),
        traversedFolders: this.traversedFolders(),
      });
    }
  }

  close(): void {
    this.dialogRef.close();
  }
}
