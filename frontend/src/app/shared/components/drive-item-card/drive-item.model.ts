export type StorageItemType = 'file' | 'folder';

export interface BaseStorageItem {
  id: string; // UUID
  ownerId: string; // UUID
  parentFolderId: string | null; // UUID
  path: string; // LTREE path string
  name: string; // file_name / folder_name
  isStarred?: boolean;
  isTrashed: boolean; // corresponds to is_trashed
  trashedAt: string | null; // TIMESTAMPTZ ISO string
  createdAt: string;
  updatedAt: string;
}

export interface DriveFileItem extends BaseStorageItem {
  itemType: 'file';
  storageKey: string;
  sizeBytes: number; // BIGINT (size_bytes)
  mimeType: string | null;
  contentHash: string | null;
  previewUrl?: string;
}

export interface DriveFolderItem extends BaseStorageItem {
  itemType: 'folder';
  itemsCount?: number;
}

export type DriveItem = DriveFileItem | DriveFolderItem;
