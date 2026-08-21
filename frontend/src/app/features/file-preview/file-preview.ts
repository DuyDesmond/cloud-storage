import { Component, Inject, OnInit, inject, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  MAT_DIALOG_DATA,
  MatDialogRef,
  MatDialogModule,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { DriveItem, DriveFileItem } from '../../shared/components/drive-item-card/drive-item.model';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';

@Component({
  selector: 'app-file-preview',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatDividerModule
  ],
  templateUrl: './file-preview.html',
  styleUrls: ['./file-preview.scss'],
})
export class FilePreview implements OnInit, OnDestroy {
  public dialogRef = inject<MatDialogRef<FilePreview>>(MatDialogRef);
  public data = inject<{ item: DriveItem }>(MAT_DIALOG_DATA);
  private fileService = inject(FileOperationsService);
  private sanitizer = inject(DomSanitizer);

  item: DriveFileItem;
  
  isLoading = signal(true);
  hasError = signal(false);
  previewUrl = signal<SafeResourceUrl | null>(null);
  rawUrl: string | null = null;
  fileType = signal<'image' | 'video' | 'pdf' | 'text' | 'unsupported'>('unsupported');

  constructor() {
    this.item = this.data.item as DriveFileItem;
    this.determineFileType();
  }

  ngOnInit(): void {
    if (this.fileType() === 'unsupported') {
      this.isLoading.set(false);
      return;
    }

    this.fileService.downloadFile(this.item.id).subscribe({
      next: (blob) => {
        this.rawUrl = URL.createObjectURL(blob);
        // Trust the URL so Angular can bind it to iframe/embed/img tags
        this.previewUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(this.rawUrl));
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load file preview', err);
        this.hasError.set(true);
        this.isLoading.set(false);
      }
    });
  }

  ngOnDestroy(): void {
    if (this.rawUrl) {
      URL.revokeObjectURL(this.rawUrl);
    }
  }

  private determineFileType(): void {
    const mime = this.item.mimeType?.toLowerCase() || '';
    if (mime.startsWith('image/')) {
      this.fileType.set('image');
    } else if (mime.startsWith('video/')) {
      this.fileType.set('video');
    } else if (mime === 'application/pdf') {
      this.fileType.set('pdf');
    } else if (mime.startsWith('text/') || mime === 'application/json' || mime === 'application/javascript') {
      this.fileType.set('text');
    } else {
      this.fileType.set('unsupported');
    }
  }

  close(): void {
    this.dialogRef.close();
  }
}
