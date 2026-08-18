import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import {
  FileOperationsService,
} from '../../core/file-operations/services/file-operations.service';
import { StorageStateService } from '../../core/file-operations/services/storage-state.service';
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
import { firstValueFrom } from 'rxjs';
import { AuthService } from '@core/auth/services/auth.service';

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
export class Trash implements OnInit {
  private fileService = inject(FileOperationsService);
  private snackBar = inject(MatSnackBar);
  readonly storageState = inject(StorageStateService);

  // State signals
  isLoading = signal<boolean>(false);
  isSidebarCollapsed = signal<boolean>(false);
  currentNav = signal<SidePanelNavKey>('trash');

  items = signal<DriveItem[]>([]);
  hasItems = computed(() => this.items().length > 0);
  private dialog = inject(MatDialog);
  private authService = inject(AuthService);
  public uploadQueueService = inject(UploadQueueService);

  ngOnInit(): void {
    this.loadTrashedItems();
    this.storageState.refreshStorageUsage();
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
        this.storageState.refreshStorageUsage();
      },
      error: (err: any) => {
        const errorMsg =
          err?.error?.detail || err?.message || 'Failed to restore item.';
        this.snackBar.open(errorMsg, 'Close', {
          duration: 4000,
        });
      },
    });
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
        this.storageState.refreshStorageUsage();
      },
      error: (err: any) => {
        const errorMsg =
          err?.error?.detail || err?.message || 'Failed to delete item permanently.';
        this.snackBar.open(errorMsg, 'Close', {
          duration: 3000,
        });
      },
    });
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
        this.storageState.refreshStorageUsage();
      },
      error: (err: any) => {
        this.isLoading.set(false);
        const errorMsg =
          err?.error?.detail || err?.message || 'Failed to empty trash.';
        this.snackBar.open(errorMsg, 'Close', {
          duration: 3000,
        });
      },
    });
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
  }

  private uploadFiles(files: File[], parentFolderId?: string): void {
    if (files.length === 0) return;
    this.uploadQueueService.enqueueFiles(files, parentFolderId);
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
}
