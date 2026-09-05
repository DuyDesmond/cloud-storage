import { Pipe, PipeTransform } from '@angular/core';
import { formatBytes } from '../utils/file-size-formatting.utils';

@Pipe({
  name: 'fileSize',
})
export class FileSizePipe implements PipeTransform {
  transform(bytes: number | null | undefined): string {
    return formatBytes(bytes);
  }
}
