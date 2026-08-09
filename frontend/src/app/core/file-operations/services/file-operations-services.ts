import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpHeaders } from '@angular/common/http';
import { forkJoin, Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { FILE_OPERATION_ENDPOINTS } from '../endpoints/file-operation-endpoints';
import {
  DriveFileItem,
  DriveFolderItem,
  DriveItem,
} from '../../../shared/components/drive-item-card/drive-item.model';

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
  constructor(private http: HttpClient) {}

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

  requestPresignedUpload(
    payload: PresignedUploadRequestPayload
  ): Observable<PresignedUploadResponsePayload> {
    return this.http.post<PresignedUploadResponsePayload>(
      FILE_OPERATION_ENDPOINTS.uploadPresign,
      payload,
      { withCredentials: true }
    );
  }

  completeDirectUpload(
    payload: CompleteUploadRequestPayload
  ): Observable<DriveFileItem> {
    return this.http
      .post<BackendFileResponse>(
        FILE_OPERATION_ENDPOINTS.uploadComplete,
        payload,
        { withCredentials: true }
      )
      .pipe(map((res) => this.toDriveFile(res)));
  }

  initiateMultipartUpload(
    payload: InitiateMultipartUploadRequestPayload
  ): Observable<InitiateMultipartUploadResponsePayload> {
    return this.http.post<InitiateMultipartUploadResponsePayload>(
      FILE_OPERATION_ENDPOINTS.multipartInitiate,
      payload,
      { withCredentials: true }
    );
  }

  presignMultipartPart(
    payload: PresignPartRequestPayload
  ): Observable<PresignPartResponsePayload> {
    return this.http.post<PresignPartResponsePayload>(
      FILE_OPERATION_ENDPOINTS.multipartPresignPart,
      payload,
      { withCredentials: true }
    );
  }

  completeMultipartUpload(
    payload: CompleteMultipartUploadRequestPayload
  ): Observable<DriveFileItem> {
    return this.http
      .post<BackendFileResponse>(
        FILE_OPERATION_ENDPOINTS.multipartComplete,
        payload,
        { withCredentials: true }
      )
      .pipe(map((res) => this.toDriveFile(res)));
  }

  abortMultipartUpload(
    payload: AbortMultipartUploadRequestPayload
  ): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      FILE_OPERATION_ENDPOINTS.multipartAbort,
      payload,
      { withCredentials: true }
    );
  }

  uploadBinaryToUrl(
    url: string,
    blob: Blob,
    headers?: Record<string, string>
  ): Observable<HttpEvent<any>> {
    let httpHeaders = new HttpHeaders();
    if (headers) {
      Object.keys(headers).forEach((k) => {
        httpHeaders = httpHeaders.set(k, headers[k]);
      });
    }

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
      .post<BackendFileResponse>(FILE_OPERATION_ENDPOINTS.uploadFiles, formData, {
        withCredentials: true,
      })
      .pipe(map((payload) => this.toDriveFile(payload)));
  }

  uploadFiles(
    files: File[],
    parentFolderId?: string
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
      { withCredentials: true }
    );
  }

  trashFolder(folderId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      FILE_OPERATION_ENDPOINTS.trashFolder(folderId),
      { withCredentials: true }
    );
  }

  createFolder(
    folderName: string,
    parentFolderId?: string
  ): Observable<DriveFolderItem> {
    return this.http
      .post<BackendFolderResponse>(
        FILE_OPERATION_ENDPOINTS.folders,
        {
          folder_name: folderName,
          parent_folder_id: parentFolderId ?? null,
        },
        { withCredentials: true }
      )
      .pipe(map((result) => this.toDriveFolder(result)));
  }
}
