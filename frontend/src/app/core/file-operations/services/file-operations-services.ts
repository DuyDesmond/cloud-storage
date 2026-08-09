import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { FILE_OPERATION_ENDPOINTS } from '../endpoints/file-operation-endpoints';
import {
  DriveFileItem,
  DriveFolderItem,
  DriveItem,
} from '../../../shared/components/drive-item-card/drive-item.model';

interface BackendFileResponse {
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

interface BackendFolderResponse {
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

@Injectable({
  providedIn: 'root',
})
export class FileOperationsService {
  constructor(private http: HttpClient) {}

  private toDriveFile(file: BackendFileResponse): DriveFileItem {
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

  private toDriveFolder(folder: BackendFolderResponse): DriveFolderItem {
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

  uploadFile(file: File, parentFolderId?: string): Observable<DriveFileItem> {
    const formData = new FormData();
    formData.append('upload_file', file);
    if (parentFolderId) {
      formData.append('parent_folder_id', parentFolderId);
    }

    return this.http
      .post<BackendFileResponse>(FILE_OPERATION_ENDPOINTS.files, formData, {
        withCredentials: true,
      })
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
}
