/**
 * Helper utilities for client-side file chunking, hashing, and filename sanitization.
 */

export const MULTIPART_THRESHOLD_BYTES = 100 * 1024 * 1024; // 100 MB
export const CHUNK_SIZE_BYTES = 8 * 1024 * 1024; // 8 MB

export function sanitizeFilename(filename: string): string {
  if (!filename) return 'unnamed_file';
  // Strip path traversal and illegal filename characters
  const clean = filename.replace(/\\/g, '/').split('/').pop() || 'unnamed_file';
  return clean.replace(/[<>:"|?*]/g, '').trim() || 'unnamed_file';
}

export function sliceFile(file: File, start: number, end: number): Blob {
  return file.slice(start, Math.min(end, file.size));
}

export async function calculateSHA256(blob: Blob | File): Promise<string> {
  const arrayBuffer = await blob.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}
