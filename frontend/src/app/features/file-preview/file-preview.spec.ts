import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { DomSanitizer } from '@angular/platform-browser';
import { By } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import { FilePreview } from './file-preview';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';

describe('FilePreview', () => {
  let fileServiceSpy: { downloadFile: ReturnType<typeof vi.fn> };
  let dialogRefSpy: { close: ReturnType<typeof vi.fn> };
  let sanitizerSpy: any;

  // Reconfigures TestBed to inject varying MAT_DIALOG_DATA per test[cite: 4]
  async function setupComponent(mimeType: string) {
    fileServiceSpy = {
      downloadFile: vi.fn().mockReturnValue(of(new Blob(['mock data']))),
    };
    dialogRefSpy = { close: vi.fn() };
    sanitizerSpy = vi.fn();

    await TestBed.configureTestingModule({
      imports: [FilePreview],
      providers: [
        { provide: FileOperationsService, useValue: fileServiceSpy },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        {
          provide: MAT_DIALOG_DATA,
          useValue: { item: { id: 'file-123', name: 'doc', mimeType } },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(FilePreview);
    const component = fixture.componentInstance;
    const sanitizer = TestBed.inject(DomSanitizer);
    sanitizerSpy = vi.spyOn(sanitizer, 'bypassSecurityTrustResourceUrl');
    return { fixture, component, sanitizerSpy };
  }

  let createUrlSpy: any;
  let revokeUrlSpy: any;

  beforeEach(() => {
    createUrlSpy = vi
      .spyOn(URL, 'createObjectURL')
      .mockReturnValue('blob:mock-url');
    revokeUrlSpy = vi
      .spyOn(URL, 'revokeObjectURL')
      .mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should parse image MIME types correctly', async () => {
    const { component, fixture } = await setupComponent('image/png');
    fixture.detectChanges();
    expect(component.fileType()).toBe('image');
  });

  it('should parse PDF MIME types correctly', async () => {
    const { component, fixture } = await setupComponent('application/pdf');
    fixture.detectChanges();
    expect(component.fileType()).toBe('pdf');
  });

  it('should abort download and set unsupported for unknown MIME types', async () => {
    const { component, fixture } = await setupComponent('application/zip');
    fixture.detectChanges();

    expect(component.fileType()).toBe('unsupported');
    expect(component.isLoading()).toBe(false);
    expect(fileServiceSpy.downloadFile).not.toHaveBeenCalled();
  });

  it('should sanitize the URL and update signals on successful download', async () => {
    const { component, fixture, sanitizerSpy } =
      await setupComponent('image/jpeg');
    fixture.detectChanges();

    expect(fileServiceSpy.downloadFile).toHaveBeenCalledWith('file-123');
    expect(createUrlSpy).toHaveBeenCalled();
    expect(sanitizerSpy).toHaveBeenCalledWith('blob:mock-url');

    // Verify signal state mutations
    expect(component.previewUrl()).toBeTruthy();
    expect(component.isLoading()).toBe(false);
    expect(component.hasError()).toBe(false);
  });

  it('should display error state if download fails', async () => {
    const { component, fixture } = await setupComponent('text/plain');
    fileServiceSpy.downloadFile.mockReturnValue(
      throwError(() => new Error('API failure')),
    );

    fixture.detectChanges();

    expect(component.hasError()).toBe(true);
    expect(component.isLoading()).toBe(false);
    expect(component.previewUrl()).toBeNull();

    const errorContainer = fixture.debugElement.query(
      By.css('.state-container.error'),
    );
    expect(errorContainer).toBeTruthy();
  });

  it('should render the correct HTML element based on fileType', async () => {
    const { fixture } = await setupComponent('application/pdf');
    fixture.detectChanges();

    const embedElement = fixture.debugElement.query(By.css('.preview-embed'));
    expect(embedElement).toBeTruthy();
    expect(embedElement.nativeElement.tagName.toLowerCase()).toBe('embed');
  });

  it('should revoke the object URL upon destruction to prevent memory leaks', async () => {
    const { component, fixture } = await setupComponent('video/mp4');
    fixture.detectChanges();

    component.ngOnDestroy();

    expect(revokeUrlSpy).toHaveBeenCalledWith('blob:mock-url');
  });

  it('should close the dialog ref when close() is invoked', async () => {
    const { component, fixture } = await setupComponent('image/png');

    component.close();
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });
});
