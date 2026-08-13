import {
  DEFAULT_STORAGE_QUOTA_BYTES,
  FileOperationsService,
} from '../../core/file-operations/services/file-operations.service';
import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { Subscription, firstValueFrom } from 'rxjs';
import { DashboardHeader } from '../../shared/components/dashboard-header/dashboard-header';
import {
  SidePanel,
  SidePanelNavKey,
} from '../../shared/components/side-panel/side-panel';
import { MobileBottomNav } from '../../shared/components/mobile-bottom-nav/mobile-bottom-nav';
import { DriveItemCard } from '../../shared/components/drive-item-card/drive-item-card';
import { DriveItem } from '../../shared/components/drive-item-card/drive-item.model';
import {
  UploadDialog,
  UploadDialogResult,
} from '../upload-dialog/upload-dialog';
import { UploadQueueService } from '../../core/file-operations/services/upload-queue-service';
import { UploadWidget } from '../upload-widget/upload-widget';
import { TraversedFolderItem } from '../../shared/utils/folder-traversal';
import { AuthService } from '@core/auth/services/auth.service';

export interface Folder {
  id: string;
  owner_id: string;
  parent_folder_id: string | null;
  folder_name: string;
  path: string;
  is_trashed: boolean;
  trashed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FileItem {
  id: string;
  owner_id: string;
  parent_folder_id: string | null;
  storage_key: string;
  file_name: string;
  size_bytes: number;
  mime_type: string;
  content_hash: string;
  path: string;
  is_trashed: boolean;
  trashed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface StorageContentResponse {
  folders: Folder[];
  files: FileItem[];
}
@Component({
  selector: 'app-drive',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    DashboardHeader,
    SidePanel,
    MobileBottomNav,
    DriveItemCard,
    UploadWidget,
  ],
  templateUrl: './drive.html',
  styleUrls: ['./drive.scss'],
})
export class Drive implements OnInit, OnDestroy {
  currentNav = signal<SidePanelNavKey>('home');
  isLoading = signal<boolean>(false);
  isSidebarCollapsed = signal<boolean>(false);

  usedBytes = signal<number>(0);
  totalBytes = signal<number>(DEFAULT_STORAGE_QUOTA_BYTES);
  usedStorageGB = computed(() => this.usedBytes() / 1024 ** 3);
  totalStorageGB = computed(() => this.totalBytes() / 1024 ** 3);

  private dialog = inject(MatDialog);
  private fileService = inject(FileOperationsService);
  private authService = inject(AuthService);
  public uploadQueueService = inject(UploadQueueService);

  private fileUploadedSub?: Subscription;

  // Items structured based on DB schema
  items = signal<DriveItem[]>([
    {
      id: 'f101',
      ownerId: 'u1',
      parentFolderId: null,
      path: 'root',
      name: 'Q4 Market Report.pdf',
      itemType: 'file',
      storageKey: 'users/u1/q4_report.pdf',
      sizeBytes: 1258291,
      mimeType: 'application/pdf',
      contentHash: null,
      isTrashed: false,
      trashedAt: null,
      createdAt: '2023-10-22T15:15:00Z',
      updatedAt: '2023-10-22T15:15:00Z',
    },
    {
      id: 'd101',
      ownerId: 'u1',
      parentFolderId: null,
      path: 'root',
      name: 'Project Assets',
      itemType: 'folder',
      itemsCount: 12,
      isTrashed: false,
      trashedAt: null,
      createdAt: '2023-09-01T10:00:00Z',
      updatedAt: '2023-09-18T09:45:00Z',
    },
  ]);

  ngOnInit(): void {
    this.fetchRootContents();
    this.fetchStorageUsage();

    this.fileUploadedSub = this.uploadQueueService.onFileUploaded.subscribe(
      (newFileItem) => {
        this.items.update((current) => [newFileItem, ...current]);
      },
    );
  }

  ngOnDestroy(): void {
    this.fileUploadedSub?.unsubscribe();
  }

  onSidebarCollapseChange(collapsed: boolean): void {
    this.isSidebarCollapsed.set(collapsed);
  }

  fetchRootContents(): void {
    this.isLoading.set(true);
    this.fileService.getStorageContents().subscribe({
      next: (data) => {
        const folderItems: DriveItem[] = data.folders.map((f) => ({
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

        const fileItems: DriveItem[] = data.files.map((f) => ({
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

        this.items.set([...folderItems, ...fileItems]);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Error fetching drive contents', err);
        this.isLoading.set(false);
      },
    });
  }

  fetchStorageUsage(): void {
    this.fileService.getStorageUsage().subscribe({
      next: ({ used_bytes }) => {
        this.usedBytes.set(used_bytes);
        this.totalBytes.set(
          this.authService.currentUser()?.storage_quota ??
            DEFAULT_STORAGE_QUOTA_BYTES,
        );
      },
    });
  }

  storagePercentage = computed(() => {
    const total = this.totalStorageGB();
    if (!total) return 0;
    return Math.min(100, Math.round((this.usedStorageGB() / total) * 100));
  });

  switchNav(nav: SidePanelNavKey) {
    this.currentNav.set(nav);
  }

  onUploadTrigger(): void {
    const dialogRef = this.dialog.open(UploadDialog, {
      width: '500px',
      disableClose: false,
    });

    dialogRef
      .afterClosed()
      .subscribe((result: UploadDialogResult | undefined) => {
        if (!result) return;

        if (result.action === 'upload') {
          if (result.files?.length) {
            this.uploadFiles(result.files);
          }
          if (result.traversedFolders?.length) {
            this.uploadFolderTree(result.traversedFolders);
          }
        } else if (result.action === 'create-folder' && result.folderName) {
          this.createFolder(result.folderName);
        }
      });
    this.fetchStorageUsage();
  }

  private uploadFiles(files: File[], parentFolderId?: string): void {
    if (files.length === 0) return;
    this.uploadQueueService.enqueueFiles(files, parentFolderId);
    this.fetchStorageUsage();
  }

  private async uploadFolderTree(
    folders: TraversedFolderItem[],
    parentFolderId?: string,
  ): Promise<void> {
    for (const folder of folders) {
      try {
        const createdFolder = await firstValueFrom(
          this.fileService.createFolder(folder.name, parentFolderId),
        );
        this.items.update((current) => [createdFolder, ...current]);

        if (folder.files.length > 0) {
          const files = folder.files.map((tf) => tf.file);
          this.uploadFiles(files, createdFolder.id);
        }

        if (folder.subfolders.length > 0) {
          await this.uploadFolderTree(folder.subfolders, createdFolder.id);
        }
      } catch (err) {
        console.error(`Failed to create folder ${folder.name}`, err);
      }
    }

    this.fetchStorageUsage();
  }

  private createFolder(folderName: string): void {
    this.fileService.createFolder(folderName).subscribe({
      next: (folder) => {
        this.items.update((current) => [folder, ...current]);
      },
      error: (error) => {
        console.error('Create folder failed:', error);
      },
    });

    this.fetchStorageUsage();
  }

  onOpenItem(item: DriveItem): void {
    if (item.itemType === 'folder') {
      console.log('Navigating to folder ID:', item.id);
    } else {
      console.log('Previewing file:', item.name);
    }
  }

  onDownloadItem(item: DriveItem): void {
    if (item.itemType !== 'file') return;

    this.fileService.downloadFile(item.id).subscribe({
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
      },
    });
  }

  onTrashItem(item: DriveItem): void {
    if (item.itemType === 'file') {
      this.fileService.trashFile(item.id).subscribe({
        next: () => {
          this.items.update((current) =>
            current.filter((entry) => entry.id !== item.id),
          );
        },
        error: (error) => {
          console.error('Trash file failed:', error);
        },
      });
    } else {
      this.fileService.trashFolder(item.id).subscribe({
        next: () => {
          this.items.update((current) =>
            current.filter((entry) => entry.id !== item.id),
          );
        },
        error: (error) => {
          console.error('Trash folder failed:', error);
        },
      });
    }
    this.fetchStorageUsage();
  }
}
