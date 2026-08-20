import {
  Component,
  OnInit,
  OnDestroy,
  signal,
  computed,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Observable, Subscription } from 'rxjs';

import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
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
export class Trash implements OnInit, OnDestroy {
  private fileService = inject(FileOperationsService);
  private snackBar = inject(MatSnackBar);
  private router = inject(Router);
  private subscriptions = new Subscription();
  readonly storageState = inject(StorageStateService);

  // State signals
  isLoading = signal<boolean>(false);
  currentNav = signal<SidePanelNavKey>('trash');

  items = signal<DriveItem[]>([]);
  hasItems = computed(() => this.items().length > 0);

  ngOnInit(): void {
    this.loadTrashedItems();
    this.storageState.refreshStorageUsage();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  loadTrashedItems(): void {
    this.isLoading.set(true);
    this.subscriptions.add(
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
      }),
    );
  }

  onRestoreItem(item: DriveItem): void {
    const restore$: Observable<unknown> =
      item.itemType === 'folder'
        ? this.fileService.restoreFolder(item.id)
        : this.fileService.restoreFile(item.id);

    this.subscriptions.add(
      restore$.subscribe({
        next: () => {
          this.items.update((list) => list.filter((i) => i.id !== item.id));
          this.snackBar.open(`"${item.name}" restored.`, 'Close', {
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
      }),
    );
  }

  onPermanentDeleteItem(item: DriveItem): void {
    if (
      !confirm(
        `Permanently delete "${item.name}"? This action cannot be undone.`,
      )
    ) {
      return;
    }

    const delete$: Observable<unknown> =
      item.itemType === 'folder'
        ? this.fileService.hardDeleteFolder(item.id)
        : this.fileService.hardDeleteFile(item.id);

    this.subscriptions.add(
      delete$.subscribe({
        next: () => {
          this.items.update((list) => list.filter((i) => i.id !== item.id));
          this.snackBar.open(`"${item.name}" permanently deleted.`, 'Close', {
            duration: 2500,
          });
          this.storageState.refreshStorageUsage();
        },
        error: (err: any) => {
          const errorMsg =
            err?.error?.detail ||
            err?.message ||
            'Failed to delete item permanently.';
          this.snackBar.open(errorMsg, 'Close', {
            duration: 3000,
          });
        },
      }),
    );
  }

  onEmptyTrash(): void {
    if (
      !confirm(
        'Permanently delete all items in the trash? This action is irreversible.',
      )
    ) {
      return;
    }

    this.isLoading.set(true);
    this.subscriptions.add(
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
      }),
    );
  }

  onUploadTrigger(): void {
    // When initiating upload from Trash page, redirect to active drive root
    this.router.navigateByUrl('/drive/root');
  }
}
