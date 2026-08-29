import { Injectable, computed, inject, signal } from '@angular/core';
import { AuthService } from '../../auth/services/auth.service';
import {
  DEFAULT_STORAGE_QUOTA_BYTES,
  FileOperationsService,
} from './file-operations.service';
import { UploadQueueService } from './upload-queue.service';

@Injectable({
  providedIn: 'root',
})
export class StorageStateService {
  private fileService = inject(FileOperationsService);
  private authService = inject(AuthService);
  private uploadQueueService = inject(UploadQueueService);

  usedBytes = signal<number>(0);
  totalBytes = signal<number>(DEFAULT_STORAGE_QUOTA_BYTES);
  isLoading = signal<boolean>(false);

  usedStorageGB = computed(() => this.usedBytes() / 1024 ** 3);
  totalStorageGB = computed(() => this.totalBytes() / 1024 ** 3);

  storagePercentage = computed(() => {
    const total = this.totalStorageGB();
    if (!total) return 0;
    return Math.min(100, Math.round((this.usedStorageGB() / total) * 100));
  });

  constructor() {
    this.refreshStorageUsage();

    // Automatically refresh storage when any upload completes
    this.uploadQueueService.onFileUploaded.subscribe(() => {
      this.refreshStorageUsage();
    });
  }

  refreshStorageUsage(): void {
    this.isLoading.set(true);
    this.fileService.getStorageUsage().subscribe({
      next: ({ used_bytes, total_bytes }) => {
        this.usedBytes.set(used_bytes);
        this.totalBytes.set(
          total_bytes ||
            DEFAULT_STORAGE_QUOTA_BYTES,
        );
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      },
    });
  }
}
