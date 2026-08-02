import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatMenuModule } from '@angular/material/menu';
import { DashboardHeader } from '../../shared/components/dashboard-header/dashboard-header';
import {
  SidePanel,
  SidePanelNavKey,
} from '../../shared/components/side-panel/side-panel';
import { MobileBottomNav } from '../../shared/components/mobile-bottom-nav/mobile-bottom-nav';

export interface DriveItem {
  id: string;
  name: string;
  type: 'image' | 'pdf' | 'video' | 'folder' | 'zip' | 'doc';
  updated: string;
  size?: string;
  itemsCount?: number;
  previewUrl?: string;
}

@Component({
  selector: 'app-drive',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatMenuModule,
    DashboardHeader,
    SidePanel,
    MobileBottomNav,
  ],
  templateUrl: './drive.html',
  styleUrls: ['./drive.scss'],
})
export class Drive {
  currentNav = signal<SidePanelNavKey>('home');

  usedStorage = signal<number>(4.2);
  totalStorage = signal<number>(15);

  storagePercentage = computed(() =>
    Math.round((this.usedStorage() / this.totalStorage()) * 100),
  );

  suggestedItems = signal<DriveItem[]>([
    {
      id: '1',
      name: 'Mountain_Retreat.jpg',
      type: 'image',
      updated: 'Oct 24, 2023, 10:20 AM',
      size: '2.4 MB',
      previewUrl:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuBIt_YtWjClysKsqMGTV1X7X5Ft3yFZgQEWcF0OHo8Gxkz3qR7_KAMsYXFRg2GMbXaU3WOIN1matFYbR6H4A5J26m1nAF0QmGuAUv_Wyxq4GjmTJAlo2_lqXGpNMHbJjD9rcJb_pGPVHNfI84jGXcasOHz-ppbKgap2Ee-mVtoOGElsiE_ir8xXbY53ItE-F-piVCzTyQqPqEL3e3l5uYViFU6SqJZNjUe9LEp4gF9BpOIe4sS_qBza',
    },
    {
      id: '2',
      name: 'Q4_Market_Report.pdf',
      type: 'pdf',
      updated: 'Oct 22, 2023, 03:15 PM',
      size: '1.2 MB',
    },
  ]);

  favoriteItems = signal<DriveItem[]>([
    {
      id: '3',
      name: 'Brand_Intro_v2.mp4',
      type: 'video',
      updated: 'Sep 18, 2023, 09:45 AM',
      size: '45.8 MB',
      previewUrl:
        'https://lh3.googleusercontent.com/aida-public/AB6AXuA0kqgSB7wp4fY6m1GxLTru7DovhA0bqnY5QTTkqfDzOBrvOdnt_JWg47y-sATjfHTPFiKG5YONAJpBdNQyWIrr0Qu1eowQL28VZTbWz9VlBDHrWoD4tlRmsnBwwz43oRtOaZB2KmUzkWMYpFp8KFJbbHAAtT_mavlN31wopEGw1gb7sy-hj-t7dtaBP0DKT1Qtz6h5cKQulcRnCgRmae2OCA3VdDqv9sb_zfTeR81Ez1jzkWIVZ8BJ',
    },
  ]);

  myFiles = signal<DriveItem[]>([
    {
      id: '4',
      name: 'Work_Project_2024',
      type: 'folder',
      updated: 'Today, 11:00 AM',
      itemsCount: 12,
    },
    {
      id: '5',
      name: 'Project_Assets_Final.zip',
      type: 'zip',
      updated: 'Yesterday, 04:30 PM',
      size: '128 MB',
    },
    {
      id: '6',
      name: 'Marketing_Copy.docx',
      type: 'doc',
      updated: 'Oct 20, 2023, 01:10 PM',
      size: '15 KB',
    },
  ]);

  onUploadTrigger() {
    // Upload logic trigger
  }

  switchNav(nav: SidePanelNavKey) {
    this.currentNav.set(nav);
  }
}
