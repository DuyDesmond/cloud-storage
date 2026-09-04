import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { UserProfile } from './user-profile';
import { AuthService } from '@core/auth/services/auth.service';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { StorageStateService } from '../../core/file-operations/services/storage-state.service';
import { signal } from '@angular/core';
import { of, Subject } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { UploadQueueService } from '../../core/file-operations/services/upload-queue.service';

describe('UserProfile', () => {
  let component: UserProfile;
  let fixture: ComponentFixture<UserProfile>;
  let mockAuthService: any;
  let mockStorageState: any;

  beforeEach(async () => {
    mockAuthService = {
      currentUser: signal({ full_name: 'Test User', email: 'test@nephos.com' }),
      logout: vi.fn().mockReturnValue(of({})),
      changePassword: vi.fn().mockReturnValue(of({ message: 'Success' })),
      deleteAccount: vi.fn().mockReturnValue(of({ message: 'Success' })),
    };

    mockStorageState = {
      refreshStorageUsage: vi.fn(),
      usedBytes: signal(1),
      totalBytes: signal(10),
      storagePercentage: signal(10),
      isLoading: signal(false),
    };

    const mockUploadQueueService = {
      onFileUploaded: new Subject(),
      activeUploadsCount: signal(0),
      hasActiveOrQueued: signal(false),
      totalProgressPercentage: signal(0),
      queue: signal([]),
    };

    await TestBed.configureTestingModule({
      imports: [UserProfile],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: mockAuthService },
        { provide: FileOperationsService, useValue: {} },
        { provide: StorageStateService, useValue: mockStorageState },
        { provide: UploadQueueService, useValue: mockUploadQueueService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UserProfile);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(component.userName()).toBe('Test User');
  });

  it('should refresh storage usage on init', () => {
    expect(mockStorageState.refreshStorageUsage).toHaveBeenCalled();
  });
});
