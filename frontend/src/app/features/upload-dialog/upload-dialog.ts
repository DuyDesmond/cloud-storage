import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';

export interface UploadDialogResult {
  action: 'upload' | 'create-folder';
  files?: File[];
  folderName?: string;
}

@Component({
  selector: 'app-upload-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    FormsModule,
  ],
  templateUrl: './upload-dialog.html',
  styleUrls: ['./upload-dialog.scss'],
})
export class UploadDialog {
  private dialogRef = inject(MatDialogRef<UploadDialog>);

  isDragging = signal(false);
  selectedFiles = signal<File[]>([]);
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

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);

    if (event.dataTransfer?.files?.length) {
      const droppedFiles = Array.from(event.dataTransfer.files);
      this.selectedFiles.update((files) => [...files, ...droppedFiles]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      const files = Array.from(input.files);
      this.selectedFiles.update((existing) => [...existing, ...files]);
    }
  }

  removeFile(index: number): void {
    this.selectedFiles.update((files) => files.filter((_, i) => i !== index));
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
    if (this.selectedFiles().length > 0) {
      this.dialogRef.close({
        action: 'upload',
        files: this.selectedFiles(),
      });
    }
  }

  close(): void {
    this.dialogRef.close();
  }
}
