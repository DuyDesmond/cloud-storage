import { environment } from '../../../../environments/environment';

export const FILE_OPERATION_ENDPOINTS = {
  files: `${environment.apiUrl}/api/v1/storage/files`,
  folders: `${environment.apiUrl}/api/v1/storage/folders`,
  downloadFile: (fileId: string) =>
    `${environment.apiUrl}/api/v1/storage/files/${fileId}/download`,
  createFolder: `${environment.apiUrl}/api/v1/storage/folders`,
  trashFile: (fileId: string) =>
    `${environment.apiUrl}/api/v1/storage/files/${fileId}`,
  trashFolder: (folderId: string) =>
    `${environment.apiUrl}/api/v1/storage/folders/${folderId}`,
};
