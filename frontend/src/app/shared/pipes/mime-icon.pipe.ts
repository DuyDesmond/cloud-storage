import { Pipe, PipeTransform } from '@angular/core';
import { getFileIcon } from '../utils/mime.utils';

@Pipe({
  name: 'mimeIcon',
})
export class MimeIconPipe implements PipeTransform {
  transform(mimeType: string | null | undefined): string {
    return getFileIcon(mimeType);
  }
}
