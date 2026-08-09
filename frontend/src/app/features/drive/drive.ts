import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
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
import { FileOperationsService } from '../../core/file-operations/services/file-operations-services';
import { UploadQueueService } from '../../core/file-operations/services/upload-queue.service';
import { UploadWidget } from '../upload-widget/upload-widget';
import { TraversedFolderItem } from '../../shared/utils/folder-traversal';

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
  usedStorage = signal<number>(5);
  totalStorage = signal<number>(20);
  currentNav = signal<SidePanelNavKey>('home');
  isLoading = signal<boolean>(false);
  isSidebarCollapsed = signal<boolean>(false);

  private dialog = inject(MatDialog);
  private fileService = inject(FileOperationsService);
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
    this.fileUploadedSub = this.uploadQueueService.onFileUploaded.subscribe(
      (newFileItem) => {
        this.items.update((current) => [newFileItem, ...current]);
      }
    );
  }

  ngOnDestroy(): void {
    this.fileUploadedSub?.unsubscribe();
  }

  onSidebarCollapseChange(collapsed: boolean): void {
    this.isSidebarCollapsed.set(collapsed);
  }

  storagePercentage = computed(() => {
    const total = this.totalStorage();
    if (!total) return 0;
    return Math.min(100, Math.round((this.usedStorage() / total) * 100));
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
  }

  private uploadFiles(files: File[], parentFolderId?: string): void {
    if (files.length === 0) return;
    this.uploadQueueService.enqueueFiles(files, parentFolderId);
  }

  private async uploadFolderTree(
    folders: TraversedFolderItem[],
    parentFolderId?: string
  ): Promise<void> {
    for (const folder of folders) {
      try {
        const createdFolder = await firstValueFrom(
          this.fileService.createFolder(folder.name, parentFolderId)
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
            current.filter((entry) => entry.id !== item.id)
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
            current.filter((entry) => entry.id !== item.id)
          );
        },
        error: (error) => {
          console.error('Trash folder failed:', error);
        },
      });
    }
  }
}
