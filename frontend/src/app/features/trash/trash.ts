import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { DriveItem } from '../../shared/components/drive-item-card/drive-item.model';
import { DashboardHeader } from '../../shared/components/dashboard-header/dashboard-header';
import {
  SidePanel,
  SidePanelNavKey,
} from '../../shared/components/side-panel/side-panel';
import { MobileBottomNav } from '../../shared/components/mobile-bottom-nav/mobile-bottom-nav';
import { UploadWidget } from '../upload-widget/upload-widget';
import { DriveItemCard } from '../../shared/components/drive-item-card/drive-item-card';
import {
  UploadDialog,
  UploadDialogResult,
} from '../upload-dialog/upload-dialog';
import { MatDialog } from '@angular/material/dialog';
import { UploadQueueService } from '@core/file-operations/services/upload-queue-service';
import { TraversedFolderItem } from '../../shared/utils/folder-traversal';
import { firstValueFrom, Subscription } from 'rxjs';

@Component({
  selector: 'app-trash',
  standalone: true,
  imports: [
    CommonModule,
    MatProgressBarModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule,
    DashboardHeader,
    SidePanel,
    MobileBottomNav,
    UploadWidget,
    DriveItemCard,
  ],
  templateUrl: './trash.html',
  styleUrls: ['./trash.scss'],
})
export class Trash {
  private fileService = inject(FileOperationsService);
  private snackBar = inject(MatSnackBar);

  // State signals
  isLoading = signal<boolean>(false);
  isSidebarCollapsed = signal<boolean>(false);
  currentNav = signal<SidePanelNavKey>('trash');
  usedBytes = signal<number>(0);
  totalBytes = signal<number>(20 * 1024 ** 3);
  usedStorageGB = computed(() => this.usedBytes() / 1024 ** 3);
  totalStorageGB = computed(() => this.totalBytes() / 1024 ** 3);

  items = signal<DriveItem[]>([]);
  hasItems = computed(() => this.items().length > 0);
  private dialog = inject(MatDialog);
  public uploadQueueService = inject(UploadQueueService);

  ngOnInit(): void {
    this.loadTrashedItems();
    this.fetchStorageUsage();
  }

  loadTrashedItems(): void {
    this.isLoading.set(true);
    this.fileService.getTrashedContents().subscribe({
      next: (data) => {
        this.items.set(
          data.sort((a, b) => (a.name || '').localeCompare(b.name || '')),
        );
        this.isLoading.set(false);
      },
      error: () => {
        this.snackBar.open('Failed to load trash contents.', 'Close', {
          duration: 3000,
        });
        this.isLoading.set(false);
      },
    });
  }

  fetchStorageUsage(): void {
    this.fileService.getStorageUsage().subscribe({
      next: ({ used_bytes, total_bytes }) => {
        this.usedBytes.set(used_bytes);
        this.totalBytes.set(total_bytes);
      },
    });
  }

  onRestoreItem(item: DriveItem): void {
    const action$: any =
      item.itemType === 'folder'
        ? this.fileService.restoreFolder(item.id)
        : this.fileService.restoreFile(item.id);

    action$.subscribe({
      next: () => {
        this.items.update((list) => list.filter((i) => i.id !== item.id));
        this.snackBar.open(`${item.name} restored.`, 'Close', {
          duration: 2500,
        });
      },
      error: () =>
        this.snackBar.open('Failed to restore item.', 'Close', {
          duration: 3000,
        }),
    });
    this.fetchStorageUsage();
  }

  onPermanentDeleteItem(item: DriveItem): void {
    // show confirmation dialog
    if (!confirm(`Permanently delete "${item.name}"? This cannot be undone.`)) {
      return;
    }

    const action$: any =
      item.itemType === 'folder'
        ? this.fileService.hardDeleteFolder(item.id)
        : this.fileService.hardDeleteFile(item.id);

    action$.subscribe({
      next: () => {
        this.items.update((list) => list.filter((i) => i.id !== item.id));
        this.snackBar.open(`${item.name} permanently deleted.`, 'Close', {
          duration: 2500,
        });
      },
      error: () =>
        this.snackBar.open('Failed to delete item permanently.', 'Close', {
          duration: 3000,
        }),
    });
    this.fetchStorageUsage();
  }

  onEmptyTrash(): void {
    if (
      !confirm(
        'Permanently delete all items in the trash? This is irreversible.',
      )
    ) {
      return;
    }

    this.isLoading.set(true);
    this.fileService.emptyTrash().subscribe({
      next: () => {
        this.items.set([]);
        this.isLoading.set(false);
        this.snackBar.open('Trash emptied successfully.', 'Close', {
          duration: 2500,
        });
      },
      error: () => {
        this.isLoading.set(false);
        this.snackBar.open('Failed to empty trash.', 'Close', {
          duration: 3000,
        });
      },
    });
    this.fetchStorageUsage();
  }

  switchNav(nav: SidePanelNavKey) {
    this.currentNav.set(nav);
  }

  onSidebarCollapseChange(collapsed: boolean): void {
    this.isSidebarCollapsed.set(collapsed);
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
}
