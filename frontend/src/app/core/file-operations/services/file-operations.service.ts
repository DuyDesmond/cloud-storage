import { Injectable, inject } from '@angular/core';
import {
  HttpClient,
  HttpEvent,
  HttpHeaders,
  HttpParams,
} from '@angular/common/http';
import { forkJoin, Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { FILE_OPERATION_ENDPOINTS } from '../endpoints/file-operations-endpoints';
import {
  DriveFileItem,
  DriveFolderItem,
  DriveItem,
} from '../../../shared/components/drive-item-card/drive-item.model';
import { StorageContentResponse } from '../../../features/drive/drive';

export const DEFAULT_STORAGE_QUOTA_BYTES = 20 * 1024 ** 3;

export interface BreadcrumbItem {
  id: string;
  name: string;
}

export interface BreadcrumbsResponse {
  breadcrumbs: BreadcrumbItem[];
}

export interface BackendFileResponse {
  id: string;
  owner_id: string;
  parent_folder_id: string | null;
  storage_key: string;
  file_name: string;
  size_bytes: number;
  mime_type: string | null;
  content_hash: string | null;
  path: string;
  is_trashed: boolean;
  trashed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BackendFolderResponse {
  id: string;
  owner_id: string;
  parent_folder_id: string | null;
  folder_name: string;
  path: string;
  is_trashed: boolean;
  trashed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PresignedUploadRequestPayload {
  file_name: string;
  size_bytes: number;
  mime_type?: string | null;
  parent_folder_id?: string | null;
  content_hash?: string | null;
}

export interface PresignedUploadResponsePayload {
  presigned_url: string;
  storage_key: string;
  expires_in: number;
  headers: Record<string, string>;
}

export interface CompleteUploadRequestPayload {
  storage_key: string;
  file_name: string;
  size_bytes: number;
  mime_type?: string | null;
  parent_folder_id?: string | null;
  content_hash?: string | null;
}

export interface InitiateMultipartUploadRequestPayload {
  file_name: string;
  size_bytes: number;
  mime_type?: string | null;
  parent_folder_id?: string | null;
  content_hash?: string | null;
}

export interface InitiateMultipartUploadResponsePayload {
  upload_id: string;
  storage_key: string;
  part_size: number;
}

export interface PresignPartRequestPayload {
  upload_id: string;
  storage_key: string;
  part_number: number;
}

export interface PresignPartResponsePayload {
  presigned_url: string;
  part_number: number;
}

export interface MultipartPartItemPayload {
  part_number: number;
  etag: string;
}

export interface CompleteMultipartUploadRequestPayload {
  upload_id: string;
  storage_key: string;
  parts: MultipartPartItemPayload[];
  file_name: string;
  size_bytes: number;
  mime_type?: string | null;
  parent_folder_id?: string | null;
  content_hash?: string | null;
}

export interface AbortMultipartUploadRequestPayload {
  upload_id: string;
  storage_key: string;
}

@Injectable({
  providedIn: 'root',
})
export class FileOperationsService {
  private http = inject(HttpClient);

  public toDriveFile(file: BackendFileResponse): DriveFileItem {
    return {
      id: file.id,
      ownerId: file.owner_id,
      parentFolderId: file.parent_folder_id,
      path: file.path,
      name: file.file_name,
      itemType: 'file',
      storageKey: file.storage_key,
      sizeBytes: file.size_bytes,
      mimeType: file.mime_type,
      contentHash: file.content_hash,
      isTrashed: file.is_trashed,
      trashedAt: file.trashed_at,
      createdAt: file.created_at,
      updatedAt: file.updated_at,
    };
  }

  public toDriveFolder(folder: BackendFolderResponse): DriveFolderItem {
    return {
      id: folder.id,
      ownerId: folder.owner_id,
      parentFolderId: folder.parent_folder_id,
      path: folder.path,
      name: folder.folder_name,
      itemType: 'folder',
      isTrashed: folder.is_trashed,
      trashedAt: folder.trashed_at,
      createdAt: folder.created_at,
      updatedAt: folder.updated_at,
    };
  }

  getStorageContents(
    parentFolderId?: string | null,
  ): Observable<StorageContentResponse> {
    let params = new HttpParams();
    if (parentFolderId) {
      params = params.set('parent_folder_id', parentFolderId);
    }

    return this.http.get<StorageContentResponse>(
      FILE_OPERATION_ENDPOINTS.getStorage,
      { params, withCredentials: true },
    );
  }

  getSharedWithMe(): Observable<StorageContentResponse> {
    return this.http.get<StorageContentResponse>(
      FILE_OPERATION_ENDPOINTS.getSharedWithMe,
      { withCredentials: true },
    );
  }

  getBreadcrumbs(
    targetId: string,
    isFile: boolean = false,
  ): Observable<BreadcrumbsResponse> {
    const params = new HttpParams()
      .set('target_id', targetId)
      .set('is_file', isFile.toString());
    return this.http.get<BreadcrumbsResponse>(
      FILE_OPERATION_ENDPOINTS.getBreadcrumbs,
      { params, withCredentials: true },
    );
  }

  getStorageUsage(): Observable<{ used_bytes: number; total_bytes: number }> {
    return this.http.get<{ used_bytes: number; total_bytes: number }>(
      FILE_OPERATION_ENDPOINTS.storageUsage,
      { withCredentials: true },
    );
  }

  getTrashedContents(): Observable<DriveItem[]> {
    return this.http
      .get<{ folders: BackendFolderResponse[]; files: BackendFileResponse[] }>(
        FILE_OPERATION_ENDPOINTS.getTrashed,
        { withCredentials: true },
      )
      .pipe(
        map((res) => {
          const folders = (res.folders || []).map((f) => this.toDriveFolder(f));
          const files = (res.files || []).map((f) => this.toDriveFile(f));
          return [...folders, ...files];
        }),
      );
  }

  restoreFile(fileId: string) {
    return this.http
      .post<BackendFileResponse>(
        FILE_OPERATION_ENDPOINTS.restoreFile(fileId),
        {},
        { withCredentials: true },
      )
      .pipe(map((r) => this.toDriveFile(r)));
  }

  restoreFolder(folderId: string) {
    return this.http
      .post<BackendFolderResponse>(
        FILE_OPERATION_ENDPOINTS.restoreFolder(folderId),
        {},
        { withCredentials: true },
      )
      .pipe(map((r) => this.toDriveFolder(r)));
  }

  hardDeleteFile(fileId: string) {
    return this.http.delete<{ message: string }>(
      FILE_OPERATION_ENDPOINTS.hardDeleteFile(fileId),
      { withCredentials: true },
    );
  }

  hardDeleteFolder(folderId: string) {
    return this.http.delete<{ message: string }>(
      FILE_OPERATION_ENDPOINTS.hardDeleteFolder(folderId),
      { withCredentials: true },
    );
  }

  emptyTrash() {
    return this.http.delete<{ message: string }>(
      FILE_OPERATION_ENDPOINTS.emptyTrash,
      { withCredentials: true },
    );
  }

  requestPresignedUpload(
    payload: PresignedUploadRequestPayload,
  ): Observable<PresignedUploadResponsePayload> {
    return this.http.post<PresignedUploadResponsePayload>(
      FILE_OPERATION_ENDPOINTS.uploadPresign,
      payload,
      { withCredentials: true },
    );
  }

  completeDirectUpload(
    payload: CompleteUploadRequestPayload,
  ): Observable<DriveFileItem> {
    return this.http
      .post<BackendFileResponse>(
        FILE_OPERATION_ENDPOINTS.uploadComplete,
        payload,
        { withCredentials: true },
      )
      .pipe(map((res) => this.toDriveFile(res)));
  }

  initiateMultipartUpload(
    payload: InitiateMultipartUploadRequestPayload,
  ): Observable<InitiateMultipartUploadResponsePayload> {
    return this.http.post<InitiateMultipartUploadResponsePayload>(
      FILE_OPERATION_ENDPOINTS.multipartInitiate,
      payload,
      { withCredentials: true },
    );
  }

  presignMultipartPart(
    payload: PresignPartRequestPayload,
  ): Observable<PresignPartResponsePayload> {
    return this.http.post<PresignPartResponsePayload>(
      FILE_OPERATION_ENDPOINTS.multipartPresignPart,
      payload,
      { withCredentials: true },
    );
  }

  completeMultipartUpload(
    payload: CompleteMultipartUploadRequestPayload,
  ): Observable<DriveFileItem> {
    return this.http
      .post<BackendFileResponse>(
        FILE_OPERATION_ENDPOINTS.multipartComplete,
        payload,
        { withCredentials: true },
      )
      .pipe(map((res) => this.toDriveFile(res)));
  }

  abortMultipartUpload(
    payload: AbortMultipartUploadRequestPayload,
  ): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      FILE_OPERATION_ENDPOINTS.multipartAbort,
      payload,
      { withCredentials: true },
    );
  }

  uploadBinaryToUrl(
    url: string,
    blob: Blob,
    headers?: Record<string, string>,
  ): Observable<HttpEvent<any>> {
    let httpHeaders = new HttpHeaders();
    if (headers) {
      Object.keys(headers).forEach((k) => {
        httpHeaders = httpHeaders.set(k, headers[k]);
      });
    }
    console.log('[upload] signed-url request', { method: 'PUT', url, headers });
    return this.http.request('PUT', url, {
      body: blob,
      headers: httpHeaders,
      reportProgress: true,
      observe: 'events',
    });
  }

  uploadFile(file: File, parentFolderId?: string): Observable<DriveFileItem> {
    const formData = new FormData();
    formData.append('upload_file', file);
    if (parentFolderId) {
      formData.append('parent_folder_id', parentFolderId);
    }

    return this.http
      .post<BackendFileResponse>(
        FILE_OPERATION_ENDPOINTS.uploadFiles,
        formData,
        {
          withCredentials: true,
        },
      )
      .pipe(map((payload) => this.toDriveFile(payload)));
  }

  uploadFiles(
    files: File[],
    parentFolderId?: string,
  ): Observable<DriveFileItem[]> {
    if (files.length === 0) {
      return of([]);
    }
    return forkJoin(files.map((file) => this.uploadFile(file, parentFolderId)));
  }

  downloadFile(fileId: string): Observable<Blob> {
    return this.http.get(FILE_OPERATION_ENDPOINTS.downloadFile(fileId), {
      responseType: 'blob',
      withCredentials: true,
    });
  }

  trashFile(fileId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      FILE_OPERATION_ENDPOINTS.trashFile(fileId),
      { withCredentials: true },
    );
  }

  trashFolder(folderId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      FILE_OPERATION_ENDPOINTS.trashFolder(folderId),
      { withCredentials: true },
    );
  }

  createFolder(
    folderName: string,
    parentFolderId?: string,
  ): Observable<DriveFolderItem> {
    return this.http
      .post<BackendFolderResponse>(
        FILE_OPERATION_ENDPOINTS.folders,
        {
          folder_name: folderName,
          parent_folder_id: parentFolderId ?? null,
        },
        { withCredentials: true },
      )
      .pipe(map((result) => this.toDriveFolder(result)));
  }

  moveFile(
    fileId: string,
    parentFolderId: string | null,
    onCollision: 'replace' | 'keep_duplicate' = 'keep_duplicate',
  ): Observable<DriveFileItem> {
    return this.http
      .patch<BackendFileResponse>(
        FILE_OPERATION_ENDPOINTS.moveFile(fileId),
        {
          parent_folder_id: parentFolderId,
          on_collision: onCollision,
        },
        { withCredentials: true },
      )
      .pipe(map((result) => this.toDriveFile(result)));
  }

  moveFolder(
    folderId: string,
    parentFolderId: string | null,
    onCollision: 'merge' | 'keep_duplicate' = 'keep_duplicate',
  ): Observable<DriveFolderItem> {
    return this.http
      .patch<BackendFolderResponse>(
        FILE_OPERATION_ENDPOINTS.moveFolder(folderId),
        {
          parent_folder_id: parentFolderId,
          on_collision: onCollision,
        },
        { withCredentials: true },
      )
      .pipe(map((result) => this.toDriveFolder(result)));
  }
}
