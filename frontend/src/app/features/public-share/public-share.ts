import { Component, OnInit, inject, signal } from '@angular/core';
import { NgOptimizedImage } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ShareService } from '../../core/share/services/share.service';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { DriveItemCard } from '../../shared/components/drive-item-card/drive-item-card';
import { Breadcrumb } from '../../shared/components/breadcrumb/breadcrumb';
import {
  DriveFileItem,
  DriveFolderItem,
} from '../../shared/components/drive-item-card/drive-item.model';
import { FilePreview } from '../file-preview/file-preview';
import { MatDialog } from '@angular/material/dialog';

@Component({
  selector: 'app-public-share',
  imports: [
    MatProgressSpinnerModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    DriveItemCard,
    Breadcrumb,
    NgOptimizedImage,
  ],
  templateUrl: './public-share.html',
  styleUrl: './public-share.scss',
})
export class PublicShareComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private shareService = inject(ShareService);
  private fileOps = inject(FileOperationsService);
  private dialog = inject(MatDialog);

  isLoading = signal(true);
  error = signal<string | null>(null);

  // General share state
  shareToken = signal<string | null>(null);
  isFile = signal<boolean>(false);
  targetId = signal<string | null>(null);

  // File specific state
  fileItem = signal<DriveFileItem | null>(null);

  // Folder specific state
  items = signal<(DriveFileItem | DriveFolderItem)[]>([]);
  breadcrumbs = signal<any[]>([]);

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const token = params.get('token');
      const folderId = params.get('id');

      if (token) {
        this.shareToken.set(token);
        this.loadShareRoot(token);
      } else if (folderId) {
        this.loadSubfolder(folderId);
      } else {
        this.error.set('Invalid link.');
        this.isLoading.set(false);
      }
    });
  }

  private loadShareRoot(token: string): void {
    this.isLoading.set(true);
    this.shareService.visitPublicLink(token).subscribe({
      next: (res: any) => {
        this.targetId.set(res.target_id);
        this.isFile.set(res.is_file);

        if (res.is_file) {
          const item: DriveFileItem = {
            id: res.target_id,
            ownerId: '',
            parentFolderId: null,
            path: '',
            name: res.file_name || 'Shared File',
            itemType: 'file',
            storageKey: '',
            sizeBytes: res.size_bytes || 0,
            mimeType: res.mime_type || '',
            contentHash: null,
            isTrashed: false,
            trashedAt: null,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };
          this.fileItem.set(item);
          this.isLoading.set(false);
        } else {
          this.fetchFolderContents(res.target_id);
        }
      },
      error: (err) => {
        this.isLoading.set(false);
        if (err.status === 404) {
          this.error.set('This link is invalid or has been revoked.');
        } else if (err.status === 403) {
          this.error.set('You do not have permission to view this link.');
        } else {
          this.error.set('Failed to access link.');
        }
      },
    });
  }

  private loadSubfolder(folderId: string): void {
    this.isFile.set(false);
    this.targetId.set(folderId);
    this.fetchFolderContents(folderId);
  }

  private fetchFolderContents(folderId: string): void {
    this.isLoading.set(true);

    this.fileOps.getStorageContents(folderId).subscribe({
      next: (res) => {
        const folders: DriveFolderItem[] = (res.folders ?? []).map((f: any) => ({
          id: f.id,
          ownerId: f.owner_id,
          parentFolderId: f.parent_folder_id,
          path: f.path,
          name: f.folder_name,
          itemType: 'folder',
          isTrashed: f.is_trashed,
          trashedAt: f.trashed_at,
          createdAt: f.created_at,
          updatedAt: f.updated_at,
        }));
        const files: DriveFileItem[] = (res.files ?? []).map((f: any) => ({
          id: f.id,
          ownerId: f.owner_id,
          parentFolderId: f.parent_folder_id,
          path: f.path,
          name: f.file_name,
          itemType: 'file',
          storageKey: f.storage_key,
          sizeBytes: f.size_bytes,
          mimeType: f.mime_type,
          contentHash: f.content_hash,
          isTrashed: f.is_trashed,
          trashedAt: f.trashed_at,
          createdAt: f.created_at,
          updatedAt: f.updated_at,
        }));
        this.items.set([...folders, ...files]);

        this.fileOps.getBreadcrumbs(folderId, false).subscribe({
          next: (bcRes) => {
            this.breadcrumbs.set(bcRes.breadcrumbs);
            this.isLoading.set(false);
          },
          error: () => {
            this.isLoading.set(false);
          },
        });
      },
      error: (err) => {
        this.isLoading.set(false);
        if (err.status === 403) {
          this.error.set('You do not have permission to view this folder.');
        } else {
          this.error.set('Failed to load folder contents.');
        }
      },
    });
  }

  onOpenItem(item: DriveFileItem | DriveFolderItem): void {
    if (item.itemType === 'folder') {
      this.router.navigate(['/public-share/folder', item.id]);
    } else {
      this.dialog.open(FilePreview, {
        width: '80vw',
        height: '80vh',
        maxWidth: '1200px',
        panelClass: 'preview-dialog-panel',
        data: { item },
      });
    }
  }

  onDownloadItem(item: DriveFileItem | DriveFolderItem): void {
    if (item.itemType === 'file') {
      this.fileOps.downloadFile(item.id).subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement('a');
          anchor.href = url;
          anchor.download = item.name;
          anchor.click();
          URL.revokeObjectURL(url);
        },
        error: (error) => {
          console.error('Download failed:', error);
        }
      });
    }
  }

  goHome(): void {
    this.router.navigate(['/']);
  }

  formatSize(bytes: number | undefined): string {
    if (bytes === undefined || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  downloadCurrentFile(): void {
    const item = this.fileItem();
    if (item) {
      this.onDownloadItem(item);
    }
  }
}
