import { environment } from '../../../../environments/environment';

export const FILE_OPERATION_ENDPOINTS = {
  getSharedWithMe: `${environment.apiUrl}/api/v1/storage/shared-with-me`,
  getBreadcrumbs: `${environment.apiUrl}/api/v1/storage/breadcrumbs`,
  uploadFiles: `${environment.apiUrl}/api/v1/storage/files`,
  folders: `${environment.apiUrl}/api/v1/storage/folders`,
  getStorage: `${environment.apiUrl}/api/v1/storage/retrieve`,
  uploadPresign: `${environment.apiUrl}/api/v1/storage/upload/presign`,
  uploadComplete: `${environment.apiUrl}/api/v1/storage/upload/complete`,
  multipartInitiate: `${environment.apiUrl}/api/v1/storage/upload/multipart/initiate`,
  multipartPresignPart: `${environment.apiUrl}/api/v1/storage/upload/multipart/presign-part`,
  multipartComplete: `${environment.apiUrl}/api/v1/storage/upload/multipart/complete`,
  multipartAbort: `${environment.apiUrl}/api/v1/storage/upload/multipart/abort`,
  downloadFile: (fileId: string) =>
    `${environment.apiUrl}/api/v1/storage/files/${fileId}/download`,
  createFolder: `${environment.apiUrl}/api/v1/storage/folders`,
  trashFile: (fileId: string) =>
    `${environment.apiUrl}/api/v1/storage/files/${fileId}`,
  trashFolder: (folderId: string) =>
    `${environment.apiUrl}/api/v1/storage/folders/${folderId}`,
  getTrashed: `${environment.apiUrl}/api/v1/storage/trash`,
  restoreFile: (fileID: string) =>
    `${environment.apiUrl}/api/v1/storage/trash/files/${fileID}/restore`,
  restoreFolder: (folderID: string) =>
    `${environment.apiUrl}/api/v1/storage/trash/folders/${folderID}/restore`,
  hardDeleteFile: (fileID: string) =>
    `${environment.apiUrl}/api/v1/storage/trash/files/${fileID}`,
  hardDeleteFolder: (folderID: string) =>
    `${environment.apiUrl}/api/v1/storage/trash/folders/${folderID}`,
  emptyTrash: `${environment.apiUrl}/api/v1/storage/trash/empty`,
  storageUsage: `${environment.apiUrl}/api/v1/storage/usage`,
};
