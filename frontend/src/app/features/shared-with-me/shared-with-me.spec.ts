import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router, ActivatedRoute } from '@angular/router';
import { SharedWithMe } from './shared-with-me';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { StorageStateService } from '../../core/file-operations/services/storage-state.service';
import { AuthService } from '../../core/auth/services/auth.service';
import { of, Subject } from 'rxjs';
import { signal } from '@angular/core';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { UploadQueueService } from '../../core/file-operations/services/upload-queue.service';

describe('SharedWithMe', () => {
  let component: SharedWithMe;
  let fixture: ComponentFixture<SharedWithMe>;
  let mockFileService: any;
  let mockStorageState: any;
  let mockRouter: any;
  let mockAuthService: any;

  beforeEach(async () => {
    mockFileService = {
      getSharedWithMe: vi.fn().mockReturnValue(of({ folders: [], files: [] })),
      getStorageContents: vi
        .fn()
        .mockReturnValue(of({ folders: [], files: [] })),
      getBreadcrumbs: vi.fn().mockReturnValue(of({ breadcrumbs: [] })),
    };

    mockStorageState = {
      refreshStorageUsage: vi.fn(),
      usedStorageGB: signal(1),
      totalStorageGB: signal(10),
      storagePercentage: signal(10),
      isLoading: signal(false),
    };

    mockAuthService = {
      currentUser: signal({ full_name: 'Test', email: 't@t.com' }),
    };

    let routerEvents = new Subject();
    mockRouter = {
      url: '/drive/shared-with-me',
      events: routerEvents,
      navigateByUrl: vi.fn(),
    };

    const mockUploadQueueService = {
      onFileUploaded: new Subject(),
      activeUploadsCount: signal(0),
      hasActiveOrQueued: signal(false),
      totalProgressPercentage: signal(0),
      queue: signal([]),
    };

    await TestBed.configureTestingModule({
      imports: [SharedWithMe],
      providers: [
        provideRouter([]),
        { provide: FileOperationsService, useValue: mockFileService },
        { provide: StorageStateService, useValue: mockStorageState },
        { provide: AuthService, useValue: mockAuthService },
        { provide: UploadQueueService, useValue: mockUploadQueueService },
        { provide: ActivatedRoute, useValue: { snapshot: { params: {} } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SharedWithMe);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
