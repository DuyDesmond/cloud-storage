import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { By } from '@angular/platform-browser';
import { of, throwError, Subject } from 'rxjs';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

import { Drive } from './drive';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { StorageStateService } from '../../core/file-operations/services/storage-state.service';
import { AuthService } from '@core/auth/services/auth.service';
import { UploadQueueService } from '../../core/file-operations/services/upload-queue.service';

describe('Drive Component', () => {
  let component: Drive;
  let fixture: ComponentFixture<Drive>;

  // Mock Subjects for event streams
  let routerEvents$: Subject<any>;
  let uploadQueue$: Subject<any>;

  // Spies
  let fileServiceSpy: any;
  let storageStateSpy: any;
  let dialogSpy: any;
  let snackBarSpy: any;
  let routerSpy: any;
  let uploadQueueServiceSpy: any;

  beforeEach(async () => {
    routerEvents$ = new Subject();
    uploadQueue$ = new Subject();

    fileServiceSpy = {
      getStorageContents: vi.fn().mockReturnValue(of({ folders: [], files: [] })),
      getBreadcrumbs: vi.fn().mockReturnValue(of({ breadcrumbs: [] })),
      createFolder: vi.fn(),
      downloadFile: vi.fn(),
      trashFile: vi.fn(),
      trashFolder: vi.fn(),
    };

    storageStateSpy = {
      refreshStorageUsage: vi.fn(),
    };

    dialogSpy = {
      open: vi.fn().mockReturnValue({ afterClosed: () => of(undefined) }),
    };

    snackBarSpy = {
      open: vi.fn(),
    };

    routerSpy = {
      url: '/drive/root',
      events: routerEvents$.asObservable(),
      navigateByUrl: vi.fn(),
    };

    uploadQueueServiceSpy = {
      onFileUploaded: uploadQueue$.asObservable(),
      enqueueFiles: vi.fn(),
    };

    // Mock global URL methods for file downloading tests
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn().mockReturnValue('blob:test-url'),
      revokeObjectURL: vi.fn(),
    });

    await TestBed.configureTestingModule({
      imports: [Drive], // Standalone component[cite: 12]
      providers: [
        { provide: FileOperationsService, useValue: fileServiceSpy },
        { provide: StorageStateService, useValue: storageStateSpy },
        { provide: MatDialog, useValue: dialogSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        { provide: Router, useValue: routerSpy },
        { provide: UploadQueueService, useValue: uploadQueueServiceSpy },
        { provide: ActivatedRoute, useValue: {} },
        { provide: AuthService, useValue: {} }
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Drive);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // --- 1. Initialization & Routing Logic ---

  it('should create and default to home navigation', () => {
    expect(component).toBeTruthy();
    expect(component.currentNav()).toBe('home');
    expect(storageStateSpy.refreshStorageUsage).toHaveBeenCalled();
  });

  it('should parse URL and update navigation context signals on router events', () => {
    // Simulate navigation to trash
    routerSpy.url = '/drive/trash';
    routerEvents$.next(new NavigationEnd(1, '/drive/trash', '/drive/trash'));

    expect(component.currentNav()).toBe('trash');
  });

  // --- 2. API & Data Fetching ---

  it('should load items from the API and map them correctly', fakeAsync(() => {
    const mockData = {
      folders: [{ id: 'f1', folder_name: 'Docs', path: '/Docs', is_trashed: false }],
      files: [{ id: 'file1', file_name: 'report.pdf', size_bytes: 1024, is_trashed: false }]
    };
    fileServiceSpy.getStorageContents.mockReturnValue(of(mockData));

    // Trigger URL resolution logic manually to force fetch
    routerSpy.url = '/drive/folder/f1';
    routerEvents$.next(new NavigationEnd(1, '/drive/folder/f1', '/drive/folder/f1'));

    tick(); // Fast-forward observables

    expect(component.isLoading()).toBe(false);
    expect(component.items().length).toBe(2);
    expect(component.items()[0].name).toBe('Docs');
    expect(component.items()[1].name).toBe('report.pdf');
  }));

  // --- 3. Edge Cases & Error Handling ---

  it('should handle 403 Forbidden errors and redirect to root', fakeAsync(() => {
    fileServiceSpy.getStorageContents.mockReturnValue(throwError(() => ({ status: 403 })));

    routerSpy.url = '/drive/folder/secret';
    routerEvents$.next(new NavigationEnd(1, '/drive/folder/secret', '/drive/folder/secret'));
    tick();

    expect(component.isLoading()).toBe(false);
    expect(snackBarSpy.open).toHaveBeenCalledWith(
      'Unauthorized: you do not have permission to access this item.',
      'Dismiss',
      { duration: 4000 }
    );
    expect(routerSpy.navigateByUrl).toHaveBeenCalledWith('/drive/root');
  }));

  it('should handle 404 Not Found errors and redirect to root', fakeAsync(() => {
    fileServiceSpy.getStorageContents.mockReturnValue(throwError(() => ({ status: 404 })));

    routerSpy.url = '/drive/folder/missing';
    routerEvents$.next(new NavigationEnd(1, '/drive/folder/missing', '/drive/folder/missing'));
    tick();

    expect(snackBarSpy.open).toHaveBeenCalledWith(
      'Unavailable: this item no longer exists or has been trashed.',
      'Dismiss',
      { duration: 4000 }
    );
  }));

  it('should immediately abort onDownloadItem if the item is a folder', () => {
    const mockFolder = { itemType: 'folder', id: '123' } as any;
    component.onDownloadItem(mockFolder);

    expect(fileServiceSpy.downloadFile).not.toHaveBeenCalled();
  });

  it('should not enqueue files or folders if upload dialog is cancelled', () => {
    dialogSpy.open.mockReturnValue({ afterClosed: () => of(undefined) });
    component.onUploadTrigger();

    expect(uploadQueueServiceSpy.enqueueFiles).not.toHaveBeenCalled();
    expect(fileServiceSpy.createFolder).not.toHaveBeenCalled();
  });

  // --- 4. Signal Streams ---

  it('should prepend newly uploaded files from the queue to the items signal', () => {
    const initialItems = [{ id: '1', itemType: 'folder', name: 'Existing' } as any];
    component.items.set(initialItems);

    const newFile = { id: '2', itemType: 'file', name: 'NewUpload.png' } as any;
    uploadQueue$.next(newFile); // Emit from service

    expect(component.items().length).toBe(2);
    expect(component.items()[0].name).toBe('NewUpload.png'); // Prepended to start
  });

  // --- 5. DOM & Control Flow Rendering Tests ---

  it('should render the loading state when isLoading is true', () => {
    component.isLoading.set(true);
    fixture.detectChanges();

    const loadingState = fixture.debugElement.query(By.css('.loading-state'));
    expect(loadingState).toBeTruthy();
    expect(loadingState.nativeElement.textContent).toContain('Retrieving contents');
  });

  it('should render the empty state if there are no items and hide the upload button if canWrite is false', () => {
    component.items.set([]);
    component.isLoading.set(false);
    component.canWrite.set(false); // Simulate read-only access
    fixture.detectChanges();

    const emptyState = fixture.debugElement.query(By.css('.empty-state'));
    expect(emptyState).toBeTruthy();

    const uploadButton = fixture.debugElement.query(By.css('.empty-state button'));
    // Button should be hidden by @if (canWrite()) control flow
    expect(uploadButton).toBeFalsy();
  });
});
