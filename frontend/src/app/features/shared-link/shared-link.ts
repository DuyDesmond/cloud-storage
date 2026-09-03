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
          if (!user) {
            this.router.navigate(['/public-share', token]);
            return of(null);
          }
          return this.shareService.visitPublicLink(token);
        }),
      )
      .subscribe({
        next: (res: any) => {
          if (!res) return; // Unauthenticated user was redirected
          this.isLoading.set(false);
          if (res.is_file) {
            this.snackBar.open('File added to Shared with me.', 'Close', {
              duration: 3000,
            });
            this.router.navigate(['/drive/shared-with-me']);
          } else {
            this.router.navigate([
              '/drive/shared-with-me/folder',
              res.target_id,
            ]);
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
