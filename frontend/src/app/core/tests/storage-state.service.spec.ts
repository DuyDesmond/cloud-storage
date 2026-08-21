import { TestBed } from '@angular/core/testing';
import { StorageStateService } from '../file-operations/services/storage-state.service';
import { FileOperationsService, DEFAULT_STORAGE_QUOTA_BYTES } from '../file-operations/services/file-operations.service';
import { AuthService } from '../auth/services/auth.service';
import { UploadQueueService } from '../file-operations/services/upload-queue.service';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Subject, of, throwError } from 'rxjs';

describe('StorageStateService', () => {
  let service: StorageStateService;
  let mockFileService: any;
  let mockAuthService: any;
  let mockUploadQueueService: any;
  let uploadSubject: Subject<void>;

  beforeEach(() => {
    uploadSubject = new Subject<void>();
    
    mockFileService = {
      getStorageUsage: vi.fn().mockReturnValue(of({ used_bytes: 1024 * 1024, total_bytes: DEFAULT_STORAGE_QUOTA_BYTES }))
    };
    
    mockAuthService = {
      currentUser: vi.fn().mockReturnValue(null)
    };
    
    mockUploadQueueService = {
      onFileUploaded: uploadSubject.asObservable()
    };

    TestBed.configureTestingModule({
      providers: [
        StorageStateService,
        { provide: FileOperationsService, useValue: mockFileService },
        { provide: AuthService, useValue: mockAuthService },
        { provide: UploadQueueService, useValue: mockUploadQueueService }
      ]
    });
    service = TestBed.inject(StorageStateService);
  });

  it('should be created and call refresh on init', () => {
    expect(service).toBeTruthy();
    expect(mockFileService.getStorageUsage).toHaveBeenCalled();
  });

  it('should compute used and total storage in GB', () => {
    expect(service.usedStorageGB()).toBeCloseTo(0.0009765625);
    expect(service.totalStorageGB()).toBe(20);
  });

  it('should refresh storage when upload completes', () => {
    mockFileService.getStorageUsage.mockClear();
    uploadSubject.next();
    expect(mockFileService.getStorageUsage).toHaveBeenCalled();
  });

  it('should handle error when refreshing storage', () => {
    mockFileService.getStorageUsage.mockReturnValue(throwError(() => new Error('error')));
    service.refreshStorageUsage();
    expect(service.isLoading()).toBe(false);
  });
});
