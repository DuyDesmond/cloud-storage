export type FilePreviewType =
  'image' | 'video' | 'pdf' | 'text' | 'unsupported';

export function getFileIcon(mimeType: string | null | undefined): string {
  const mime = (mimeType || '').toLowerCase();
  if (mime.startsWith('image/')) return 'image';
  if (mime.startsWith('video/')) return 'movie';
  if (mime.includes('pdf')) return 'picture_as_pdf';
  return 'description';
}

export function getFileType(
  mimeType: string | null | undefined,
): FilePreviewType {
  const mime = (mimeType || '').toLowerCase();
  if (mime.startsWith('image/')) {
    return 'image';
  } else if (mime.startsWith('video/')) {
    return 'video';
  } else if (mime === 'application/pdf') {
    return 'pdf';
  } else if (
    mime.startsWith('text/') ||
    mime === 'application/json' ||
    mime === 'application/javascript'
  ) {
    return 'text';
  }
  return 'unsupported';
}
