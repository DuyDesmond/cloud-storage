import {
  Component,
  OnInit,
  inject,
  signal,
  OnDestroy,
  DestroyRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
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
import {
  DriveItem,
  DriveFileItem,
} from '../../shared/components/drive-item-card/drive-item.model';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { getFileType, FilePreviewType } from '../../shared/utils/mime.utils';

@Component({
  selector: 'app-file-preview',
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatDividerModule,
  ],
  templateUrl: './file-preview.html',
  styleUrl: './file-preview.scss',
})
export class FilePreview implements OnInit, OnDestroy {
  public dialogRef = inject<MatDialogRef<FilePreview>>(MatDialogRef);
  public data = inject<{ item: DriveItem }>(MAT_DIALOG_DATA);
  private fileService = inject(FileOperationsService);
  private sanitizer = inject(DomSanitizer);
  private destroyRef = inject(DestroyRef);

  item: DriveFileItem;

  isLoading = signal(true);
  hasError = signal(false);
  previewUrl = signal<SafeResourceUrl | null>(null);
  rawUrl: string | null = null;
  fileType = signal<FilePreviewType>('unsupported');

  constructor() {
    this.item = this.data.item as DriveFileItem;
    this.determineFileType();
  }

  ngOnInit(): void {
    if (this.fileType() === 'unsupported') {
      this.isLoading.set(false);
      return;
    }

    this.fileService
      .downloadFile(this.item.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          this.rawUrl = URL.createObjectURL(blob);
          // Trust the URL so Angular can bind it to iframe/embed/img tags
          this.previewUrl.set(
            this.sanitizer.bypassSecurityTrustResourceUrl(this.rawUrl),
          );
          this.isLoading.set(false);
        },
        error: (err: unknown) => {
          console.error('Failed to load file preview', err);
          this.hasError.set(true);
          this.isLoading.set(false);
        },
      });
  }

  ngOnDestroy(): void {
    if (this.rawUrl) {
      URL.revokeObjectURL(this.rawUrl);
    }
  }

  private determineFileType(): void {
    this.fileType.set(getFileType(this.item.mimeType));
  }

  close(): void {
    this.dialogRef.close();
  }
}
