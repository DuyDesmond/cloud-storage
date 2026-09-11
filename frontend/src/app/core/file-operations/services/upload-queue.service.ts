import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpEventType, HttpHeaders } from '@angular/common/http';
import { Subject, Subscription, firstValueFrom } from 'rxjs';
import {
  FileOperationsService,
  PresignedUploadResponsePayload,
  InitiateMultipartUploadResponsePayload,
  PresignPartResponsePayload,
} from './file-operations.service';
import { DriveFileItem } from '../../../shared/components/drive-item-card/drive-item.model';
import {
  CHUNK_SIZE_BYTES,
  MULTIPART_THRESHOLD_BYTES,
  sanitizeFilename,
  sliceFile,
} from './file-chunking';

export type UploadStatus =
  'queued' | 'uploading' | 'paused' | 'completed' | 'error' | 'cancelled';

export interface UploadQueueItem {
  id: string;
  file: File;
  name: string;
  sizeBytes: number;
  parentFolderId?: string;
  progressPercentage: number;
  speedBytesPerSec: number;
  etaSeconds: number;
  uploadedBytes: number;
  status: UploadStatus;
  errorMessage?: string;
  driveItem?: DriveFileItem;
  // Internal tracking properties
  startTime?: number;
  lastLoadedBytes?: number;
  lastTimestamp?: number;
  uploadId?: string;
  storageKey?: string;
  completedParts?: { part_number: number; etag: string }[];
  subscription?: Subscription;
}

const MAX_CONCURRENT_UPLOADS = 3;
const LOCAL_STORAGE_PREFIX = 'nephos_upload_resume_';

@Injectable({
  providedIn: 'root',
})
export class UploadQueueService {
  private fileService = inject(FileOperationsService);

  queue = signal<UploadQueueItem[]>([]);
  onFileUploaded = new Subject<DriveFileItem>();

  activeUploadsCount = computed(
    () => this.queue().filter((item) => item.status === 'uploading').length,
  );

  hasActiveOrQueued = computed(() =>
    this.queue().some(
      (item) => item.status === 'uploading' || item.status === 'queued',
    ),
  );

  totalProgressPercentage = computed(() => {
    const items = this.queue();
    if (items.length === 0) return 0;
    const totalBytes = items.reduce((sum, item) => sum + item.sizeBytes, 0);
    if (totalBytes === 0) return 100;
    const uploadedBytes = items.reduce(
      (sum, item) => sum + item.uploadedBytes,
      0,
    );
    return Math.min(100, Math.round((uploadedBytes / totalBytes) * 100));
  });

  enqueueFiles(files: File[], parentFolderId?: string): void {
    const newItems: UploadQueueItem[] = files.map((file) => {
      const id = `${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      return {
        id,
        file,
        name: sanitizeFilename(file.name),
        sizeBytes: file.size,
        parentFolderId,
        progressPercentage: 0,
        speedBytesPerSec: 0,
        etaSeconds: 0,
        uploadedBytes: 0,
        status: 'queued',
        completedParts: [],
      };
    });

    this.queue.update((current) => [...current, ...newItems]);
    this.processQueue();
  }

  pauseUpload(id: string): void {
    this.queue.update((items) =>
      items.map((item) => {
        if (item.id === id && item.status === 'uploading') {
          item.subscription?.unsubscribe();
          return { ...item, status: 'paused' as UploadStatus };
        }
        return item;
      }),
    );
    this.processQueue();
  }

  resumeUpload(id: string): void {
    this.queue.update((items) =>
      items.map((item) => {
        if (
          item.id === id &&
          (item.status === 'paused' || item.status === 'error')
        ) {
          return {
            ...item,
            status: 'queued' as UploadStatus,
            errorMessage: undefined,
          };
        }
        return item;
      }),
    );
    this.processQueue();
  }

  cancelUpload(id: string): void {
    const item = this.queue().find((i) => i.id === id);
    if (item) {
      item.subscription?.unsubscribe();
      if (item.uploadId && item.storageKey) {
        this.fileService
          .abortMultipartUpload({
            upload_id: item.uploadId,
            storage_key: item.storageKey,
          })
          .subscribe({ error: () => {} });
        this.clearResumeState(item.file);
      }
    }
    this.queue.update((items) => items.filter((i) => i.id !== id));
    this.processQueue();
  }

  pauseAll(): void {
    this.queue().forEach((item) => {
      if (item.status === 'uploading') {
        this.pauseUpload(item.id);
      } else if (item.status === 'queued') {
        this.queue.update((items) =>
          items.map((i) =>
            i.id === item.id ? { ...i, status: 'paused' as UploadStatus } : i,
          ),
        );
      }
    });
  }

  resumeAll(): void {
    this.queue.update((items) =>
      items.map((i) =>
        i.status === 'paused' || i.status === 'error'
          ? { ...i, status: 'queued' as UploadStatus, errorMessage: undefined }
          : i,
      ),
    );
    this.processQueue();
  }

  clearCompleted(): void {
    this.queue.update((items) =>
      items.filter(
        (i) =>
          i.status === 'uploading' ||
          i.status === 'queued' ||
          i.status === 'paused',
      ),
    );
  }

  private processQueue(): void {
    const items = this.queue();
    const activeCount = items.filter((i) => i.status === 'uploading').length;
    const slotsAvailable = MAX_CONCURRENT_UPLOADS - activeCount;

    if (slotsAvailable <= 0) return;

    const queuedItems = items.filter((i) => i.status === 'queued');
    const toStart = queuedItems.slice(0, slotsAvailable);

    for (const item of toStart) {
      this.startUpload(item.id);
    }
  }

  private async startUpload(id: string): Promise<void> {
    this.updateItemState(id, {
      status: 'uploading',
      startTime: Date.now(),
      lastLoadedBytes: 0,
      lastTimestamp: Date.now(),
    });

    const item = this.queue().find((i) => i.id === id);
    if (!item) return;

    try {
      if (item.sizeBytes > MULTIPART_THRESHOLD_BYTES) {
        await this.uploadMultipartFile(item);
      } else {
        await this.uploadSingleFile(item);
      }
    } catch (err: any) {
      const errorMsg =
        err?.error?.detail ||
        err?.message ||
        'Upload failed due to network error.';
      this.updateItemState(id, {
        status: 'error',
        errorMessage: errorMsg,
        speedBytesPerSec: 0,
        etaSeconds: 0,
      });
      this.processQueue();
    }
  }

  private async uploadSingleFile(item: UploadQueueItem): Promise<void> {
    const presignRes: PresignedUploadResponsePayload =
      await this.retryWithBackoff(() =>
        firstValueFrom(
          this.fileService.requestPresignedUpload({
            file_name: item.name,
            size_bytes: item.sizeBytes,
            mime_type: item.file.type || 'application/octet-stream',
            parent_folder_id: item.parentFolderId ?? null,
          }),
        ),
      );

    await new Promise<void>((resolve, reject) => {
      const sub = this.fileService
        .uploadBinaryToUrl(
          presignRes.presigned_url,
          item.file,
          presignRes.headers,
        )
        .subscribe({
          next: (event: any) => {
            //  Removed '&& event.total' check; fallback to item.sizeBytes
            if (event.type === HttpEventType.UploadProgress) {
              const total = event.total || item.sizeBytes;
              this.calculateProgress(item.id, event.loaded, total);
            } else if (event.type === HttpEventType.Response) {
              this.calculateProgress(item.id, item.sizeBytes, item.sizeBytes);
              resolve();
            }
          },
          error: (err) => reject(err),
        });

      this.updateItemState(item.id, { subscription: sub });
    });

    const driveItem = await this.retryWithBackoff(() =>
      firstValueFrom(
        this.fileService.completeDirectUpload({
          storage_key: presignRes.storage_key,
          file_name: item.name,
          size_bytes: item.sizeBytes,
          mime_type: item.file.type || null,
          parent_folder_id: item.parentFolderId ?? null,
        }),
      ),
    );

    this.updateItemState(item.id, {
      status: 'completed',
      progressPercentage: 100,
      uploadedBytes: item.sizeBytes,
      speedBytesPerSec: 0,
      etaSeconds: 0,
      driveItem,
    });

    this.onFileUploaded.next(driveItem);
    this.processQueue();
  }

  private async uploadMultipartFile(item: UploadQueueItem): Promise<void> {
    let resumeState = this.getResumeState(item.file);
    let uploadId: string;
    let storageKey: string;
    let completedParts: { part_number: number; etag: string }[] = [];

    if (resumeState) {
      uploadId = resumeState.uploadId;
      storageKey = resumeState.storageKey;
      completedParts = resumeState.completedParts || [];
    } else {
      const initRes: InitiateMultipartUploadResponsePayload =
        await this.retryWithBackoff(() =>
          firstValueFrom(
            this.fileService.initiateMultipartUpload({
              file_name: item.name,
              size_bytes: item.sizeBytes,
              mime_type: item.file.type || 'application/octet-stream',
              parent_folder_id: item.parentFolderId ?? null,
            }),
          ),
        );
      uploadId = initRes.upload_id;
      storageKey = initRes.storage_key;
      this.saveResumeState(item.file, uploadId, storageKey, []);
    }

    this.updateItemState(item.id, { uploadId, storageKey, completedParts });

    const totalParts = Math.ceil(item.sizeBytes / CHUNK_SIZE_BYTES);

    for (let partNum = 1; partNum <= totalParts; partNum++) {
      const currentItem = this.queue().find((i) => i.id === item.id);
      if (!currentItem || currentItem.status !== 'uploading') return;

      const existing = completedParts.find((p) => p.part_number === partNum);
      if (existing) {
        const loaded = Math.min(partNum * CHUNK_SIZE_BYTES, item.sizeBytes);
        this.calculateProgress(item.id, loaded, item.sizeBytes);
        continue;
      }

      const start = (partNum - 1) * CHUNK_SIZE_BYTES;
      const end = Math.min(start + CHUNK_SIZE_BYTES, item.sizeBytes);
      const chunk = sliceFile(item.file, start, end);

      const presignPartRes: PresignPartResponsePayload =
        await this.retryWithBackoff(() =>
          firstValueFrom(
            this.fileService.presignMultipartPart({
              upload_id: uploadId,
              storage_key: storageKey,
              part_number: partNum,
            }),
          ),
        );

      let partETag = '';
      await new Promise<void>((resolve, reject) => {
        const sub = this.fileService
          .uploadBinaryToUrl(presignPartRes.presigned_url, chunk)
          .subscribe({
            next: (event: any) => {
              //  Fallback to item.sizeBytes if event.total is omitted
              if (event.type === HttpEventType.UploadProgress) {
                const totalLoaded = start + event.loaded;
                this.calculateProgress(item.id, totalLoaded, item.sizeBytes);
              } else if (event.type === HttpEventType.Response) {
                const etagHeader =
                  event.headers.get('ETag') || event.headers.get('etag');
                partETag = etagHeader
                  ? etagHeader.replace(/"/g, '')
                  : `etag_part_${partNum}`;
                const loadedNow = Math.min(end, item.sizeBytes);
                this.calculateProgress(item.id, loadedNow, item.sizeBytes);
                resolve();
              }
            },
            error: (err) => reject(err),
          });

        this.updateItemState(item.id, { subscription: sub });
      });

      completedParts.push({ part_number: partNum, etag: partETag });
      this.saveResumeState(item.file, uploadId, storageKey, completedParts);
    }

    const driveItem = await this.retryWithBackoff(() =>
      firstValueFrom(
        this.fileService.completeMultipartUpload({
          upload_id: uploadId,
          storage_key: storageKey,
          parts: completedParts,
          file_name: item.name,
          size_bytes: item.sizeBytes,
          mime_type: item.file.type || null,
          parent_folder_id: item.parentFolderId ?? null,
        }),
      ),
    );

    this.clearResumeState(item.file);

    this.updateItemState(item.id, {
      status: 'completed',
      progressPercentage: 100,
      uploadedBytes: item.sizeBytes,
      speedBytesPerSec: 0,
      etaSeconds: 0,
      driveItem,
    });

    this.onFileUploaded.next(driveItem);
    this.processQueue();
  }

  private calculateProgress(id: string, loaded: number, total: number): void {
    const item = this.queue().find((i) => i.id === id);
    if (!item) return;

    const now = Date.now();
    const lastTime = item.lastTimestamp || now;
    const timeDiffSec = (now - lastTime) / 1000;

    let speed = item.speedBytesPerSec;

    if (timeDiffSec >= 0.2) {
      const bytesDiff = loaded - (item.lastLoadedBytes || 0);
      const instantSpeed = bytesDiff / timeDiffSec;
      speed = speed === 0 ? instantSpeed : speed * 0.7 + instantSpeed * 0.3;
    }

    const remainingBytes = Math.max(0, total - loaded);
    const etaSeconds = speed > 0 ? Math.ceil(remainingBytes / speed) : 0;
    const progressPercentage = Math.min(
      100,
      Math.round((loaded / total) * 100),
    );

    this.updateItemState(id, {
      uploadedBytes: loaded,
      progressPercentage,
      speedBytesPerSec: Math.max(0, speed),
      etaSeconds,
      lastTimestamp: now,
      lastLoadedBytes: loaded,
    });
  }

  private updateItemState(
    id: string,
    patchItem: Partial<UploadQueueItem>,
  ): void {
    this.queue.update((items) =>
      items.map((i) => (i.id === id ? { ...i, ...patchItem } : i)),
    );
  }

  private async retryWithBackoff<T>(
    fn: () => Promise<T>,
    maxRetries = 3,
    delayMs = 1000,
  ): Promise<T> {
    let attempt = 0;
    while (true) {
      try {
        return await fn();
      } catch (err: any) {
        if (err?.status && err.status >= 400 && err.status < 500) {
          throw err;
        }
        attempt++;
        if (attempt >= maxRetries) {
          throw err;
        }
        await new Promise((res) =>
          setTimeout(res, delayMs * Math.pow(2, attempt - 1)),
        );
      }
    }
  }

  private getResumeState(file: File): {
    uploadId: string;
    storageKey: string;
    completedParts: { part_number: number; etag: string }[];
  } | null {
    try {
      const key = `${LOCAL_STORAGE_PREFIX}${file.name}_${file.size}`;
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  }

  private saveResumeState(
    file: File,
    uploadId: string,
    storageKey: string,
    completedParts: { part_number: number; etag: string }[],
  ): void {
    try {
      const key = `${LOCAL_STORAGE_PREFIX}${file.name}_${file.size}`;
      localStorage.setItem(
        key,
        JSON.stringify({ uploadId, storageKey, completedParts }),
      );
    } catch {}
  }

  private clearResumeState(file: File): void {
    try {
      const key = `${LOCAL_STORAGE_PREFIX}${file.name}_${file.size}`;
      localStorage.removeItem(key);
    } catch {}
  }
}
