import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.services';
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
export class Trash {
  private fileService = inject(FileOperationsService);
  private snackBar = inject(MatSnackBar);

  // State signals
  isLoading = signal<boolean>(false);
  isSidebarCollapsed = signal<boolean>(false);
  currentNav = signal<SidePanelNavKey>('trash');
  usedStorage = signal<number>(5);
  totalStorage = signal<number>(20);

  items = signal<DriveItem[]>([]);
  hasItems = computed(() => this.items().length > 0);
  ngOnInit(): void {
    this.loadTrashedItems();
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
      },
      error: () =>
        this.snackBar.open('Failed to restore item.', 'Close', {
          duration: 3000,
        }),
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
      },
      error: () =>
        this.snackBar.open('Failed to delete item permanently.', 'Close', {
          duration: 3000,
        }),
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
      },
      error: () => {
        this.isLoading.set(false);
        this.snackBar.open('Failed to empty trash.', 'Close', {
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
    // Triggers upload modal if initiated from navigation
  }
}
