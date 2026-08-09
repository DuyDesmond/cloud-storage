import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  UploadQueueService,
  UploadQueueItem,
} from '../../core/file-operations/services/upload-queue.service';

@Component({
  selector: 'app-upload-widget',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatTooltipModule,
  ],
  templateUrl: './upload-widget.html',
  styleUrls: ['./upload-widget.scss'],
})
export class UploadWidget {
  uploadQueueService = inject(UploadQueueService);
  isExpanded = signal<boolean>(true);

  toggleExpand(): void {
    this.isExpanded.update((v) => !v);
  }

  formatSpeed(bytesPerSec: number): string {
    if (!bytesPerSec || bytesPerSec <= 0) return '0 B/s';
    const k = 1024;
    const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    const i = Math.floor(Math.log(bytesPerSec) / Math.log(k));
    return `${parseFloat((bytesPerSec / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }

  formatEta(seconds: number): string {
    if (!seconds || seconds <= 0) return '';
    if (seconds < 60) return `${seconds}s remaining`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s remaining`;
  }

  formatSize(bytes: number): string {
    if (!bytes || bytes <= 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  }

  pauseUpload(id: string, event: Event): void {
    event.stopPropagation();
    this.uploadQueueService.pauseUpload(id);
  }

  resumeUpload(id: string, event: Event): void {
    event.stopPropagation();
    this.uploadQueueService.resumeUpload(id);
  }

  cancelUpload(id: string, event: Event): void {
    event.stopPropagation();
    this.uploadQueueService.cancelUpload(id);
  }

  pauseAll(): void {
    this.uploadQueueService.pauseAll();
  }

  resumeAll(): void {
    this.uploadQueueService.resumeAll();
  }

  clearCompleted(): void {
    this.uploadQueueService.clearCompleted();
  }
}
