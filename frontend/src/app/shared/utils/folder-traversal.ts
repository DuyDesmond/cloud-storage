export interface TraversedFileItem {
  file: File;
  relativePath: string;
}

export interface TraversedFolderItem {
  name: string;
  relativePath: string;
  files: TraversedFileItem[];
  subfolders: TraversedFolderItem[];
}

export interface DragAndDropResult {
  files: TraversedFileItem[];
  folders: TraversedFolderItem[];
}

/**
 * Traverses DataTransferItems dropped into HTML5 drag and drop zone
 * using Webkit FileSystem API (webkitGetAsEntry).
 */
export async function traverseDataTransferItems(
  items: DataTransferItemList,
): Promise<DragAndDropResult> {
  const resultFiles: TraversedFileItem[] = [];
  const resultFolders: TraversedFolderItem[] = [];

  const entries: any[] = [];
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.kind === 'file') {
      const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
      if (entry) {
        entries.push(entry);
      } else {
        const file = item.getAsFile();
        if (file) {
          resultFiles.push({ file, relativePath: file.name });
        }
      }
    }
  }

  for (const entry of entries) {
    if (entry.isFile) {
      const file = await getFileFromEntry(entry);
      if (file) {
        resultFiles.push({ file, relativePath: entry.fullPath || file.name });
      }
    } else if (entry.isDirectory) {
      const folder = await readDirectoryEntry(entry, '');
      resultFolders.push(folder);
    }
  }

  return { files: resultFiles, folders: resultFolders };
}

function getFileFromEntry(fileEntry: any): Promise<File | null> {
  return new Promise((resolve) => {
    fileEntry.file(
      (file: File) => resolve(file),
      () => resolve(null),
    );
  });
}

function readDirectoryEntry(
  dirEntry: any,
  parentPath: string,
): Promise<TraversedFolderItem> {
  return new Promise((resolve) => {
    const folderPath = parentPath
      ? `${parentPath}/${dirEntry.name}`
      : dirEntry.name;
    const folderItem: TraversedFolderItem = {
      name: dirEntry.name,
      relativePath: folderPath,
      files: [],
      subfolders: [],
    };

    const dirReader = dirEntry.createReader();
    const readEntries = () => {
      dirReader.readEntries(async (entries: any[]) => {
        if (!entries.length) {
          resolve(folderItem);
          return;
        }

        for (const entry of entries) {
          if (entry.isFile) {
            const file = await getFileFromEntry(entry);
            if (file) {
              folderItem.files.push({
                file,
                relativePath: `${folderPath}/${file.name}`,
              });
            }
          } else if (entry.isDirectory) {
            const sub = await readDirectoryEntry(entry, folderPath);
            folderItem.subfolders.push(sub);
          }
        }

        readEntries(); // Read next batch until empty
      });
    };

    readEntries();
  });
}
