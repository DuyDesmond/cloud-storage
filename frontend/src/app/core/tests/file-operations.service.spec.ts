import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import {
  FileOperationsService,
  BackendFileResponse,
  BackendFolderResponse,
} from '../file-operations/services/file-operations.service';
import { FILE_OPERATION_ENDPOINTS } from '../file-operations/endpoints/file-operations-endpoints';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('FileOperationsService', () => {
  let service: FileOperationsService;
  let httpMock: HttpTestingController;

  const mockBackendFile: BackendFileResponse = {
    id: 'f1',
    owner_id: 'u1',
    parent_folder_id: null,
    storage_key: 'sk1',
    file_name: 'test.txt',
    size_bytes: 123,
    mime_type: 'text/plain',
    content_hash: 'hash',
    path: 'root.f1',
    is_trashed: false,
    trashed_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const mockBackendFolder: BackendFolderResponse = {
    id: 'd1',
    owner_id: 'u1',
    parent_folder_id: null,
    folder_name: 'test folder',
    path: 'root.d1',
    is_trashed: false,
    trashed_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        FileOperationsService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(FileOperationsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should map BackendFileResponse to DriveFileItem', () => {
    const item = service.toDriveFile(mockBackendFile);
    expect(item.id).toBe('f1');
    expect(item.itemType).toBe('file');
    expect(item.name).toBe('test.txt');
  });

  it('should map BackendFolderResponse to DriveFolderItem', () => {
    const item = service.toDriveFolder(mockBackendFolder);
    expect(item.id).toBe('d1');
    expect(item.itemType).toBe('folder');
    expect(item.name).toBe('test folder');
  });

  it('should get storage contents', () => {
    service.getStorageContents('folder-1').subscribe((res) => {
      expect(res).toBeTruthy();
    });

    const req = httpMock.expectOne(
      (request) =>
        request.url === FILE_OPERATION_ENDPOINTS.getStorage &&
        request.params.get('parent_folder_id') === 'folder-1',
    );
    expect(req.request.method).toBe('GET');
    req.flush({ folders: [], files: [], path: [] });
  });

  it('should request presigned upload', () => {
    const payload = { file_name: 'test.txt', size_bytes: 123 };
    service.requestPresignedUpload(payload).subscribe((res) => {
      expect(res.presigned_url).toBe('http://test.url');
    });

    const req = httpMock.expectOne(FILE_OPERATION_ENDPOINTS.uploadPresign);
    expect(req.request.method).toBe('POST');
    req.flush({
      presigned_url: 'http://test.url',
      storage_key: 'sk1',
      expires_in: 3600,
      headers: {},
    });
  });
});
