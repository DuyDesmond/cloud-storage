import { Component, Inject, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
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
import { ShareService, ShareState, SharedUser } from '../../core/share/services/share.service';

@Component({
  selector: 'app-share-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './share-dialog.html',
  styleUrls: ['./share-dialog.scss'],
})
export class ShareDialog implements OnInit {
  private shareService = inject(ShareService);
  private fb = inject(FormBuilder);

  item: DriveItem;
  isFile: boolean;

  isLoading = signal(true);
  shareState = signal<ShareState | null>(null);

  shareUserForm: FormGroup;
  publicLinkForm: FormGroup;

  constructor(
    public dialogRef: MatDialogRef<ShareDialog>,
    @Inject(MAT_DIALOG_DATA) public data: { item: DriveItem }
  ) {
    this.item = data.item;
    this.isFile = this.item.itemType === 'file';

    this.shareUserForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      permission: ['view']
    });

    this.publicLinkForm = this.fb.group({
      enabled: [false],
      permission: ['view']
    });
  }

  ngOnInit(): void {
    this.loadShareState();

    this.publicLinkForm.get('enabled')?.valueChanges.subscribe(enabled => {
      this.updatePublicLink(enabled, this.publicLinkForm.value.permission);
    });

    this.publicLinkForm.get('permission')?.valueChanges.subscribe(permission => {
      if (this.publicLinkForm.value.enabled) {
        this.updatePublicLink(true, permission);
      }
    });
  }

  loadShareState(): void {
    this.isLoading.set(true);
    this.shareService.getShareState(this.item.id, this.isFile).subscribe({
      next: (state) => {
        this.shareState.set(state);
        this.publicLinkForm.patchValue({
          enabled: state.public_link.enabled,
          permission: state.public_link.permission
        }, { emitEvent: false });
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load share state', err);
        this.isLoading.set(false);
      }
    });
  }

  addUserShare(): void {
    if (this.shareUserForm.invalid) return;

    const { email, permission } = this.shareUserForm.value;

    this.shareService.shareWithUser(this.item.id, this.isFile, email, permission).subscribe({
      next: () => {
        this.shareUserForm.reset({ permission: 'view' });
        this.loadShareState();
      },
      error: (err) => {
        console.error('Failed to add user share', err);
      }
    });
  }

  updateUserPermission(user: SharedUser, permission: 'view' | 'edit'): void {
    this.shareService.shareWithUser(this.item.id, this.isFile, user.email, permission).subscribe({
      next: () => {
        this.loadShareState();
      },
      error: (err) => {
        console.error('Failed to update user permission', err);
      }
    });
  }

  removeUserShare(user: SharedUser): void {
    this.shareService.revokeUserShare(this.item.id, this.isFile, user.email).subscribe({
      next: () => {
        this.loadShareState();
      },
      error: (err) => {
        console.error('Failed to remove user share', err);
      }
    });
  }

  updatePublicLink(enabled: boolean, permission: 'view' | 'edit'): void {
    this.shareService.setPublicLink(this.item.id, this.isFile, enabled, permission).subscribe({
      next: () => {
        this.loadShareState();
      },
      error: (err) => {
        console.error('Failed to update public link', err);
      }
    });
  }

  copyLink(): void {
    const state = this.shareState();
    if (state?.public_link.link) {
      // In a real app, generate the full URL. Here we just use a placeholder domain + token.
      const fullUrl = `${window.location.origin}/shared/${state.public_link.link}`;
      navigator.clipboard.writeText(fullUrl);
    }
  }

  close(): void {
    this.dialogRef.close();
  }
}
