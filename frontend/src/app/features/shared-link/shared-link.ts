import { Component, OnInit, inject, signal } from '@angular/core';

import { ActivatedRoute, Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ShareService } from '../../core/share/services/share.service';
import { AuthService } from '../../core/auth/services/auth.service';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { FilePreview } from '../file-preview/file-preview';
import { DriveFileItem } from '../../shared/components/drive-item-card/drive-item.model';
import { catchError, of, switchMap } from 'rxjs';

@Component({
  selector: 'app-shared-link',
  imports: [MatProgressSpinnerModule, MatSnackBarModule],
  templateUrl: './shared-link.html',
  styleUrl: './shared-link.scss',
})
export class SharedLinkComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private shareService = inject(ShareService);
  private authService = inject(AuthService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  currentUser = this.authService.currentUser;
  isLoading = signal(true);
  error = signal<string | null>(null);

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('token');

    if (!token) {
      this.error.set('Invalid link.');
      this.isLoading.set(false);
      return;
    }

    this.authService
      .getProfile()
      .pipe(
        catchError(() => of(null)),
        switchMap((user) => {
          return this.shareService.visitPublicLink(token);
        }),
      )
      .subscribe({
        next: (res: any) => {
          this.isLoading.set(false);
          if (res.is_file) {
            if (this.currentUser()) {
              this.snackBar.open('File added to Shared with me.', 'Close', {
                duration: 3000,
              });
              this.router.navigate(['/drive/shared-with-me']);
            } else {
              const fileItem: DriveFileItem = {
                id: res.target_id,
                ownerId: '',
                parentFolderId: null,
                path: '',
                name: res.file_name || 'Shared File',
                itemType: 'file',
                storageKey: '',
                sizeBytes: res.size_bytes || 0,
                mimeType: res.mime_type || '',
                contentHash: null,
                isTrashed: false,
                trashedAt: null,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
              };
              this.dialog.open(FilePreview, {
                width: '80vw',
                height: '80vh',
                maxWidth: '1200px',
                panelClass: 'preview-dialog-panel',
                data: { item: fileItem },
              });
            }
          } else {
            if (this.currentUser()) {
              this.router.navigate([
                '/drive/shared-with-me/folder',
                res.target_id,
              ]);
            } else {
              this.error.set('Folders cannot be viewed.');
            }
          }
        },
        error: (err) => {
          this.isLoading.set(false);
          if (err.status === 404) {
            this.error.set('This link is invalid or has been revoked.');
          } else {
            this.error.set('Failed to access link.');
          }
        },
      });
  }

  goHome(): void {
    this.router.navigate(['/drive/root']);
  }
}
