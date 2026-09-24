import { Component, input, output } from '@angular/core';
import { NgOptimizedImage } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-dashboard-header',
  imports: [RouterModule, MatButtonModule, MatIconModule, NgOptimizedImage],
  templateUrl: './dashboard-header.html',
  styleUrl: './dashboard-header.scss',
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
