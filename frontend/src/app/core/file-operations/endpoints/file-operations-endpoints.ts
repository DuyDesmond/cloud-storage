import { environment } from '../../../../environments/environment';

export const FILE_OPERATION_ENDPOINTS = {
  getSharedWithMe: `${environment.apiUrl}${environment.apiStr}/storage/shared-with-me`,
  getBreadcrumbs: `${environment.apiUrl}${environment.apiStr}/storage/breadcrumbs`,
  uploadFiles: `${environment.apiUrl}${environment.apiStr}/storage/files`,
  folders: `${environment.apiUrl}${environment.apiStr}/storage/folders`,
  getStorage: `${environment.apiUrl}${environment.apiStr}/storage/retrieve`,
  uploadPresign: `${environment.apiUrl}${environment.apiStr}/storage/upload/presign`,
  uploadComplete: `${environment.apiUrl}${environment.apiStr}/storage/upload/complete`,
  multipartInitiate: `${environment.apiUrl}${environment.apiStr}/storage/upload/multipart/initiate`,
  multipartPresignPart: `${environment.apiUrl}${environment.apiStr}/storage/upload/multipart/presign-part`,
  multipartComplete: `${environment.apiUrl}${environment.apiStr}/storage/upload/multipart/complete`,
  multipartAbort: `${environment.apiUrl}${environment.apiStr}/storage/upload/multipart/abort`,
  downloadFile: (fileId: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/files/${fileId}/download`,
  moveFile: (fileId: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/files/${fileId}/move`,
  createFolder: `${environment.apiUrl}${environment.apiStr}/storage/folders`,
  moveFolder: (folderId: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/folders/${folderId}/move`,
  trashFile: (fileId: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/files/${fileId}`,
  trashFolder: (folderId: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/folders/${folderId}`,
  getTrashed: `${environment.apiUrl}${environment.apiStr}/storage/trash`,
  restoreFile: (fileID: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/trash/files/${fileID}/restore`,
  restoreFolder: (folderID: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/trash/folders/${folderID}/restore`,
  hardDeleteFile: (fileID: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/trash/files/${fileID}`,
  hardDeleteFolder: (folderID: string) =>
    `${environment.apiUrl}${environment.apiStr}/storage/trash/folders/${folderID}`,
  emptyTrash: `${environment.apiUrl}${environment.apiStr}/storage/trash/empty`,
  storageUsage: `${environment.apiUrl}${environment.apiStr}/storage/usage`,
};
