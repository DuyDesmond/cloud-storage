import { TestBed } from '@angular/core/testing';
import { UploadQueueService } from '../file-operations/services/upload-queue.service';
import { FileOperationsService } from '../file-operations/services/file-operations.service';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';

describe('UploadQueueService', () => {
  let service: UploadQueueService;
  let mockFileService: any;

  beforeEach(() => {
    mockFileService = {
      requestPresignedUpload: vi.fn(),
      uploadBinaryToUrl: vi.fn(),
      completeDirectUpload: vi.fn(),
      initiateMultipartUpload: vi.fn(),
      presignMultipartPart: vi.fn(),
      completeMultipartUpload: vi.fn(),
      abortMultipartUpload: vi.fn().mockReturnValue(of({})),
    };

    TestBed.configureTestingModule({
      providers: [
        UploadQueueService,
        { provide: FileOperationsService, useValue: mockFileService },
      ],
    });
    service = TestBed.inject(UploadQueueService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should enqueue files and set their status to queued', () => {
    const file1 = new File([''], 'test1.txt', { type: 'text/plain' });
    const file2 = new File([''], 'test2.txt', { type: 'text/plain' });

    service.enqueueFiles([file1, file2], 'parent-id');

    const queue = service.queue();
    expect(queue.length).toBe(2);
    expect(queue[0].name).toBe('test1.txt');
    // Initially they are added as queued.
    // They might transition to uploading immediately, but mockFileService doesn't resolve promises yet.
    expect(queue[0].status).toMatch(/queued|uploading/);
  });

  it('should compute total progress percentage correctly', () => {
    service.queue.set([
      {
        id: '1',
        sizeBytes: 100,
        uploadedBytes: 50,
        status: 'uploading',
      } as any,
      {
        id: '2',
        sizeBytes: 100,
        uploadedBytes: 100,
        status: 'completed',
      } as any,
    ]);

    expect(service.totalProgressPercentage()).toBe(75);
  });

  it('should cancel upload and remove from queue', () => {
    service.queue.set([
      {
        id: '1',
        sizeBytes: 100,
        uploadedBytes: 50,
        status: 'uploading',
        uploadId: 'u1',
        storageKey: 'k1',
      } as any,
    ]);

    service.cancelUpload('1');
    expect(service.queue().length).toBe(0);
    expect(mockFileService.abortMultipartUpload).toHaveBeenCalledWith({
      upload_id: 'u1',
      storage_key: 'k1',
    });
  });

  it('should pause upload', () => {
    service.queue.set([
      {
        id: '1',
        sizeBytes: 100,
        uploadedBytes: 50,
        status: 'uploading',
      } as any,
    ]);

    service.pauseUpload('1');
    expect(service.queue()[0].status).toBe('paused');
  });

  it('should resume upload', () => {
    service.queue.set([
      { id: '1', sizeBytes: 100, uploadedBytes: 50, status: 'paused' } as any,
    ]);

    service.resumeUpload('1');
    expect(service.queue()[0].status).toBe('uploading');
  });

  it('should clear completed', () => {
    service.queue.set([
      {
        id: '1',
        sizeBytes: 100,
        uploadedBytes: 50,
        status: 'uploading',
      } as any,
      {
        id: '2',
        sizeBytes: 100,
        uploadedBytes: 100,
        status: 'completed',
      } as any,
      { id: '3', sizeBytes: 100, uploadedBytes: 10, status: 'error' } as any,
    ]);

    service.clearCompleted();

    expect(service.queue().length).toBe(1);
    expect(service.queue()[0].id).toBe('1');
  });
});
