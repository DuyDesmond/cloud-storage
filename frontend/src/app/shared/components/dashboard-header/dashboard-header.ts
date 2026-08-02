import { Component, EventEmitter, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { HostBinding } from '@angular/core';

@Component({
  selector: 'app-dashboard-header',
  standalone: true,
  imports: [CommonModule, RouterModule, MatButtonModule, MatIconModule],
  templateUrl: './dashboard-header.html',
  styleUrls: ['./dashboard-header.scss'],
})
export class DashboardHeader {
  searchPlaceholder = input<string>('Search files...');

  // Signal Outputs
  upload = output<void>();
  profile = output<void>();
  searchChange = output<string>();

  onSearchChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.searchChange.emit(value);
  }

  onProfileClick(): void {}
}
