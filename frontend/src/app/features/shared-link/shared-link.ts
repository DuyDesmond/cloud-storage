import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ShareService } from '../../core/share/services/share.service';
import { AuthService } from '../../core/auth/services/auth.service';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

@Component({
  selector: 'app-shared-link',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, MatSnackBarModule],
  templateUrl: './shared-link.html',
  styleUrl: './shared-link.scss'
})
export class SharedLinkComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private shareService = inject(ShareService);
  private authService = inject(AuthService);
  private snackBar = inject(MatSnackBar);

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

    // check is logged in
    this.authService.getProfile().subscribe({
      next: (user) => {
        if (!user) {
          // if not logged in, redirect to login.
          this.router.navigate(['/login'], { queryParams: { returnUrl: `/shared/${token}` } });
          return;
        }

        // if user is logged in, attempt to visit link
        this.shareService.visitPublicLink(token).subscribe({
          next: (res) => {
            if (res.is_file) {
              this.snackBar.open('File added to Shared with me.', 'Close', { duration: 3000 });
              this.router.navigate(['/drive/shared-with-me']);
            } else {
              this.router.navigate(['/drive/shared-with-me/folder', res.target_id]);
            }
          },
          error: (err) => {
            this.isLoading.set(false);
            if (err.status === 404) {
              this.error.set('This link is invalid or has been revoked.');
            } else {
              this.error.set('Failed to access link.');
            }
          }
        });
      },
      error: () => {
        // if error fetching user, redirect to login
        this.router.navigate(['/login'], { queryParams: { returnUrl: `/shared/${token}` } });
      }
    });
  }

  goHome(): void {
    this.router.navigate(['/']);
  }
}
