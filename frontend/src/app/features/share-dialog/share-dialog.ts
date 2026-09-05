import { Component, OnInit, inject, signal, DestroyRef } from '@angular/core';

import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  MAT_DIALOG_DATA,
  MatDialogRef,
  MatDialogModule,
} from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { DriveItem } from '../../shared/components/drive-item-card/drive-item.model';
import {
  ShareService,
  ShareState,
  SharedUser,
} from '../../core/share/services/share.service';

@Component({
  selector: 'app-share-dialog',
  imports: [
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './share-dialog.html',
  styleUrl: './share-dialog.scss',
})
export class ShareDialog implements OnInit {
  private shareService = inject(ShareService);
  private fb = inject(FormBuilder);
  private destroyRef = inject(DestroyRef);

  item: DriveItem;
  isFile: boolean;

  isLoading = signal(true);
  shareState = signal<ShareState | null>(null);

  shareUserForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    permission: ['view'],
    password: [''],
  });

  publicLinkForm = this.fb.group({
    enabled: [false],
    permission: ['view'],
    password: [''],
  });

  public dialogRef = inject<MatDialogRef<ShareDialog>>(MatDialogRef);
  public data = inject<{ item: DriveItem }>(MAT_DIALOG_DATA);

  constructor() {
    this.item = this.data.item;
    this.isFile = this.item.itemType === 'file';
  }

  ngOnInit(): void {
    this.loadShareState();

    this.publicLinkForm
      .get('enabled')
      ?.valueChanges.pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((enabled) => {
        if (!enabled) {
          this.updatePublicLink();
        }
      });
  }

  loadShareState(): void {
    this.isLoading.set(true);
    this.shareService
      .getShareState(this.item.id, this.isFile)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (state) => {
          this.shareState.set(state);
          this.publicLinkForm.patchValue(
            {
              enabled: state.public_link.enabled,
              permission: state.public_link.permission,
            },
            { emitEvent: false },
          );
          this.isLoading.set(false);
        },
        error: (err: unknown) => {
          // TODO: Replaced implicit any with unknown
          console.error('Failed to load share state', err);
          this.isLoading.set(false);
        },
      });
  }

  addUserShare(): void {
    if (this.shareUserForm.invalid) return;

    const { email, permission, password } = this.shareUserForm.getRawValue();
    if (!email) return;
    const validPermission = (permission === 'edit' ? 'edit' : 'view') as
      'view' | 'edit';

    this.shareService
      .shareWithUser(
        this.item.id,
        this.isFile,
        email,
        validPermission,
        password ?? undefined,
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.shareUserForm.reset({ permission: 'view', password: '' });
          this.loadShareState();
        },
        error: (err: unknown) => {
          console.error('Failed to add user share', err);
        },
      });
  }

  updateUserPermission(user: SharedUser, permission: 'view' | 'edit'): void {
    this.shareService
      .shareWithUser(this.item.id, this.isFile, user.email, permission)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.loadShareState();
        },
        error: (err: unknown) => {
          console.error('Failed to update user permission', err);
        },
      });
  }

  removeUserShare(user: SharedUser): void {
    this.shareService
      .revokeUserShare(this.item.id, this.isFile, user.email)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.loadShareState();
        },
        error: (err: unknown) => {
          console.error('Failed to remove user share', err);
        },
      });
  }

  updatePublicLink(): void {
    const { enabled, permission, password } = this.publicLinkForm.getRawValue();
    const validPermission = (permission === 'edit' ? 'edit' : 'view') as
      'view' | 'edit';
    this.shareService
      .setPublicLink(
        this.item.id,
        this.isFile,
        enabled ?? false,
        validPermission,
        password ?? undefined,
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.loadShareState();
        },
        error: (err: unknown) => {
          console.error('Failed to update public link', err);
        },
      });
  }

  copyLink(): void {
    const state = this.shareState();
    if (state?.public_link.link) {
      const fullUrl = `${window.location.origin}/shared/${state.public_link.link}`;
      navigator.clipboard.writeText(fullUrl);
    }
  }

  close(): void {
    this.dialogRef.close();
  }
}
