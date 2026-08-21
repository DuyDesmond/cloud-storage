import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { Trash } from './trash';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { StorageStateService } from '../../core/file-operations/services/storage-state.service';
import { AuthService } from '../../core/auth/services/auth.service';
import { UploadQueueService } from '../../core/file-operations/services/upload-queue.service';
import { of, Subject } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('Trash', () => {
  let component: Trash;
  let fixture: ComponentFixture<Trash>;
  let mockFileService: any;
  let mockStorageState: any;

  beforeEach(async () => {
    mockFileService = {
      getTrashedContents: vi.fn().mockReturnValue(of([])),
      emptyTrash: vi.fn().mockReturnValue(of({ message: 'Success' }))
    };

    mockStorageState = {
      refreshStorageUsage: vi.fn(),
      usedBytes: vi.fn().mockReturnValue(0),
      usedStorageGB: signal(1),
      totalStorageGB: signal(10),
      storagePercentage: signal(10),
      isLoading: signal(false)
    };

    await TestBed.configureTestingModule({
      imports: [Trash],
      providers: [
        provideRouter([]),
        { provide: FileOperationsService, useValue: mockFileService },
        { provide: StorageStateService, useValue: mockStorageState },
        { provide: AuthService, useValue: { currentUser: vi.fn().mockReturnValue(null) } },
        { provide: UploadQueueService, useValue: { onFileUploaded: new Subject(), activeUploadsCount: vi.fn().mockReturnValue(0), hasActiveOrQueued: vi.fn().mockReturnValue(false), totalProgressPercentage: vi.fn().mockReturnValue(0), queue: vi.fn().mockReturnValue([]) } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(Trash);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load trashed items on init', () => {
    expect(mockFileService.getTrashedContents).toHaveBeenCalled();
  });
});
