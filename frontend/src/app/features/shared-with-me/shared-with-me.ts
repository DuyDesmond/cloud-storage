import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subscription, Subject, switchMap, of, catchError } from 'rxjs';

import { DEFAULT_STORAGE_QUOTA_BYTES, FileOperationsService, BreadcrumbItem } from '../../core/file-operations/services/file-operations.service';
import { AuthService } from '@core/auth/services/auth.service';
import { DashboardHeader } from '../../shared/components/dashboard-header/dashboard-header';
import { SidePanel, SidePanelNavKey } from '../../shared/components/side-panel/side-panel';
import { MobileBottomNav } from '../../shared/components/mobile-bottom-nav/mobile-bottom-nav';
import { DriveItemCard } from '../../shared/components/drive-item-card/drive-item-card';
import { DriveItem } from '../../shared/components/drive-item-card/drive-item.model';
import { ShareDialog } from '../share-dialog/share-dialog';

@Component({
  selector: 'app-shared-with-me',
  standalone: true,
  imports: [
    CommonModule, RouterModule, MatIconModule, MatButtonModule,
    MatProgressBarModule, MatSnackBarModule, DashboardHeader,
    SidePanel, MobileBottomNav, DriveItemCard
  ],
  templateUrl: './shared-with-me.html',
  styleUrls: ['../drive/drive.scss'] // Reusing drive layout styles
})
export class SharedWithMe implements OnInit, OnDestroy {
  currentNav = signal<SidePanelNavKey>('shared');
  isLoading = signal<boolean>(false);
  isSidebarCollapsed = signal<boolean>(false);

  usedBytes = signal<number>(0);
  totalBytes = signal<number>(DEFAULT_STORAGE_QUOTA_BYTES);

  currentFolderId = signal<string | null>(null);
  breadcrumbs = signal<BreadcrumbItem[]>([]);
  pageTitle = signal<string>('Shared with me');

  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private router = inject(Router);
  private fileService = inject(FileOperationsService);
  private authService = inject(AuthService);

  private subscriptions = new Subscription();
  private routeChange$ = new Subject<string | null>();
  private initialized = false;

  items = signal<DriveItem[]>([]);

  ngOnInit(): void {
    this.fetchStorageUsage();

    this.subscriptions.add(
      this.routeChange$.pipe(
        switchMap((folderId) => {
          this.isLoading.set(true);
          this.items.set([]);

          const fetchReq = folderId === null
            ? this.fileService.getSharedWithMe()
            : this.fileService.getStorageContents(folderId);

          return fetchReq.pipe(
            catchError((err) => {
              this.handleFetchError(err);
              return of({ folders: [], files: [] });
            })
          );
        })
      ).subscribe((data: any) => {
        const folderItems: DriveItem[] = (data.folders ?? []).map((f: any) => ({
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

        const fileItems: DriveItem[] = (data.files ?? []).map((f: any) => ({
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
      })
    );

    this.subscriptions.add(
      this.router.events.subscribe(() => {
        this.resolveContextFromUrl(this.router.url);
      })
    );

    this.resolveContextFromUrl(this.router.url);
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
    this.routeChange$.complete();
  }

  private resolveContextFromUrl(url: string): void {
    const path = url.split('?')[0].split('#')[0];
    const parts = path.split('/').filter(Boolean);
    const folderIdx = parts.indexOf('folder');
    const folderId = folderIdx !== -1 ? (parts[folderIdx + 1] ?? null) : null;

    if (this.initialized && this.currentFolderId() === folderId) return;
    this.initialized = true;

    this.currentFolderId.set(folderId);

    if (folderId) {
      this.fetchBreadcrumbs(folderId);
      document.title = 'Nephos - Loading...';
    } else {
      this.breadcrumbs.set([]);
      this.pageTitle.set('Shared with me');
      document.title = 'Nephos - Shared with me';
    }

    this.routeChange$.next(folderId);
  }

  private fetchBreadcrumbs(folderId: string): void {
    this.fileService.getBreadcrumbs(folderId, false).subscribe({
      next: (res) => {
        this.breadcrumbs.set(res.breadcrumbs);
        const last = res.breadcrumbs[res.breadcrumbs.length - 1];
        if (last) {
          this.pageTitle.set(last.name);
          document.title = `Nephos - ${last.name}`;
        }
      },
      error: () => this.breadcrumbs.set([])
    });
  }

  private handleFetchError(err: any): void {
    this.isLoading.set(false);
    this.snackBar.open('Unable to access this shared item.', 'Dismiss', { duration: 4000 });
    this.router.navigateByUrl('/drive/shared-with-me');
  }

  fetchStorageUsage(): void {
    this.fileService.getStorageUsage().subscribe({
      next: ({ used_bytes }) => {
        this.usedBytes.set(used_bytes);
        this.totalBytes.set(this.authService.currentUser()?.storage_quota ?? DEFAULT_STORAGE_QUOTA_BYTES);
      },
    });
  }

  switchNav(nav: SidePanelNavKey) {
    if (nav !== 'shared') this.router.navigateByUrl(`/drive/root`);
  }

  onSidebarCollapseChange(collapsed: boolean): void {
    this.isSidebarCollapsed.set(collapsed);
  }

  onOpenItem(item: DriveItem): void {
    if (item.itemType === 'folder') {
      this.router.navigateByUrl(`/drive/shared-with-me/folder/${item.id}`);
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
      }
    });
  }

  onShareItem(item: DriveItem): void {
    this.dialog.open(ShareDialog, { width: '600px', data: { item } });
  }
}
