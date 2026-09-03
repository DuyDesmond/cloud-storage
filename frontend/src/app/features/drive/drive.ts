import {
  FileOperationsService,
  BreadcrumbItem,
} from '../../core/file-operations/services/file-operations.service';
import { StorageStateService } from '../../core/file-operations/services/storage-state.service';
import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
  OnDestroy,
  DestroyRef,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subject, switchMap, of, catchError, firstValueFrom } from 'rxjs';
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
import { UploadQueueService } from '../../core/file-operations/services/upload-queue.service';
import { UploadWidget } from '../upload-widget/upload-widget';
import { TraversedFolderItem } from '../../shared/utils/folder-traversal';
import { AuthService } from '@core/auth/services/auth.service';
import { ShareDialog } from '../share-dialog/share-dialog';
import { FilePreview } from '../file-preview/file-preview';
import { Breadcrumb } from '../../shared/components/breadcrumb/breadcrumb';

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

type DriveSection = 'root' | 'shared-with-me';

@Component({
  selector: 'app-drive',
  imports: [
    RouterModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatSnackBarModule,
    DashboardHeader,
    SidePanel,
    MobileBottomNav,
    DriveItemCard,
    UploadWidget,
    Breadcrumb,
  ],
  templateUrl: './drive.html',
  styleUrl: './drive.scss',
})
export class Drive implements OnInit, OnDestroy {
  readonly storageState = inject(StorageStateService);

  currentNav = signal<SidePanelNavKey>('home');
  isLoading = signal<boolean>(false);
  // Current navigation state
  currentSection = signal<DriveSection>('root');
  currentFolderId = signal<string | null>(null);
  breadcrumbs = signal<BreadcrumbItem[]>([]);
  pageTitle = signal<string>('Cloud Drive');

  // Whether the user can upload/create in the current view
  canWrite = signal<boolean>(true);

  private destroyRef = inject(DestroyRef);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private fileService = inject(FileOperationsService);
  private authService = inject(AuthService);
  public uploadQueueService = inject(UploadQueueService);

  /** Emits a new context each time the route changes; switchMap cancels previous in-flight request. */
  private routeChange$ = new Subject<{ folderId: string | null }>();
  /** Prevents double-fetch guard from blocking the very first load. */
  private initialized = false;

  items = signal<DriveItem[]>([]);

  ngOnInit(): void {
    this.storageState.refreshStorageUsage();

    // switchMap ensures previous fetch is cancelled when route changes (AbortController equivalent)
    this.routeChange$
      .pipe(
        switchMap((ctx) => {
          this.isLoading.set(true);
          this.items.set([]);
          this.canWrite.set(true);

          return this.fileService.getStorageContents(ctx.folderId).pipe(
            catchError((err) => {
              this.handleFetchError(err);
              return of({ folders: [], files: [] });
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((data: StorageContentResponse) => {
        const folderItems: DriveItem[] = (data.folders ?? []).map(
          (f: Folder) => ({
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
          }),
        );

        const fileItems: DriveItem[] = (data.files ?? []).map(
          (f: FileItem) => ({
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
          }),
        );

        this.items.set([...folderItems, ...fileItems]);
        this.isLoading.set(false);
      });

    // Listen to the full URL to determine context (works across all route patterns)
    this.router.events
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        const url = this.router.url;
        this.resolveContextFromUrl(url);
      });

    // Trigger initial load
    this.resolveContextFromUrl(this.router.url);

    this.uploadQueueService.onFileUploaded
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((newFileItem) => {
        this.items.update((current) => [newFileItem, ...current]);
      });
  }

  ngOnDestroy(): void {
    this.routeChange$.complete();
  }

  private resolveContextFromUrl(url: string): void {
    // Remove query params and fragments, then split
    const path = url.split('?')[0].split('#')[0];
    const parts = path.split('/').filter(Boolean); // remove empty strings
    const folderIdx = parts.indexOf('folder');
    const folderId = folderIdx !== -1 ? (parts[folderIdx + 1] ?? null) : null;

    const prevFolderId = this.currentFolderId();
    const prevNav = this.currentNav();
    let newNav: SidePanelNavKey = 'home';

    if (path.includes('shared-with-me')) {
      newNav = 'shared';
    } else if (path.includes('trash')) {
      newNav = 'trash';
    } else if (path.includes('starred')) {
      newNav = 'home';
    } else if (path.includes('recent')) {
      newNav = 'recent';
    }

    // Skip if nothing changed (prevents double-fetching on router events that aren't navigations)
    if (this.initialized && prevFolderId === folderId && prevNav === newNav)
      return;
    this.initialized = true;

    this.currentFolderId.set(folderId);
    this.currentNav.set(newNav);

    if (folderId) {
      this.fetchBreadcrumbs(folderId, false);
      document.title = 'Nephos - Loading...';
    } else {
      this.breadcrumbs.set([]);
      this.pageTitle.set('Cloud Drive');
      document.title = `Nephos - Cloud Drive`;
    }

    this.routeChange$.next({ folderId });
  }

  private fetchBreadcrumbs(folderId: string, isFile: boolean): void {
    this.fileService
      .getBreadcrumbs(folderId, isFile)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.breadcrumbs.set(res.breadcrumbs);
          const last = res.breadcrumbs[res.breadcrumbs.length - 1];
          if (last) {
            this.pageTitle.set(last.name);
            document.title = `Nephos - ${last.name}`;
          }
        },
        error: () => {
          this.breadcrumbs.set([]);
        },
      });
  }

  private handleFetchError(err: unknown): void {
    this.isLoading.set(false);
    const errorStatus = (err as { status?: number })?.status;
    if (errorStatus === 403) {
      this.snackBar.open(
        'Unauthorized: you do not have permission to access this item.',
        'Dismiss',
        { duration: 4000 },
      );
      this.router.navigateByUrl('/drive/root');
    } else if (errorStatus === 404 || errorStatus === 410) {
      this.snackBar.open(
        'Unavailable: this item no longer exists or has been trashed.',
        'Dismiss',
        { duration: 4000 },
      );
      this.router.navigateByUrl('/drive/root');
    }
  }

  onUploadTrigger(): void {
    if (!this.canWrite()) return;

    const dialogRef = this.dialog.open(UploadDialog, {
      width: '500px',
      disableClose: false,
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result: UploadDialogResult | undefined) => {
        if (!result) return;

        const parentId = this.currentFolderId() ?? undefined;
        if (result.action === 'upload') {
          if (result.files?.length) {
            this.uploadFiles(result.files, parentId);
          }
          if (result.traversedFolders?.length) {
            this.uploadFolderTree(result.traversedFolders, parentId);
          }
        } else if (result.action === 'create-folder' && result.folderName) {
          this.createFolder(result.folderName, parentId);
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

  private createFolder(folderName: string, parentFolderId?: string): void {
    this.fileService
      .createFolder(folderName, parentFolderId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
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
      const section = this.currentSection();
      this.router.navigateByUrl(`/drive/${section}/folder/${item.id}`);
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

  onDownloadItem(item: DriveItem): void {
    if (item.itemType !== 'file') return;

    this.fileService
      .downloadFile(item.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
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

  onShareItem(item: DriveItem): void {
    this.dialog.open(ShareDialog, {
      width: '600px',
      data: { item },
    });
  }

  onTrashItem(item: DriveItem): void {
    if (item.itemType === 'file') {
      this.fileService
        .trashFile(item.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.items.update((current) =>
              current.filter((entry) => entry.id !== item.id),
            );
            this.storageState.refreshStorageUsage();
          },
          error: (error) => {
            console.error('Trash file failed:', error);
          },
        });
    } else {
      this.fileService
        .trashFolder(item.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.items.update((current) =>
              current.filter((entry) => entry.id !== item.id),
            );
            this.storageState.refreshStorageUsage();
          },
          error: (error) => {
            console.error('Trash folder failed:', error);
          },
        });
    }
  }
}
