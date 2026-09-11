import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PublicShareComponent } from './public-share';
import { vi } from 'vitest';
import { ActivatedRoute, Router } from '@angular/router';
import { ShareService } from '../../core/share/services/share.service';
import { FileOperationsService } from '../../core/file-operations/services/file-operations.service';
import { MatDialog } from '@angular/material/dialog';
import { of, throwError } from 'rxjs';

describe('PublicShareComponent', () => {
  let component: PublicShareComponent;
  let fixture: ComponentFixture<PublicShareComponent>;
  let mockRouter: any;
  let mockShareService: any;
  let mockFileOps: any;
  let mockDialog: any;

  beforeEach(async () => {
    mockRouter = {
      navigate: vi.fn()
    };

    mockShareService = {
      visitPublicLink: vi.fn().mockReturnValue(of({
        is_file: false,
        target_id: 'test-folder-id'
      }))
    };

    mockFileOps = {
      getStorageContents: vi.fn().mockReturnValue(of({
        folders: [{
          id: 'folder-123',
          owner_id: 'owner-1',
          parent_folder_id: 'test-folder-id',
          folder_name: 'Child folder',
          path: 'root.child',
          is_trashed: false,
          trashed_at: null,
          created_at: '2026-09-01T10:00:00Z',
          updated_at: '2026-09-02T10:00:00Z',
        }],
        files: [{
          id: 'file-123',
          owner_id: 'owner-1',
          parent_folder_id: 'test-folder-id',
          file_name: 'child.txt',
          storage_key: 'files/child.txt',
          size_bytes: 2048,
          mime_type: 'text/plain',
          content_hash: null,
          path: 'root.child.file',
          is_trashed: false,
          trashed_at: null,
          created_at: '2026-09-01T10:00:00Z',
          updated_at: '2026-09-02T10:00:00Z',
        }]
      })),
      getBreadcrumbs: vi.fn().mockReturnValue(of({
        breadcrumbs: []
      })),
      downloadFile: vi.fn().mockReturnValue(of(new Blob()))
    };

    mockDialog = {
      open: vi.fn()
    };

    await TestBed.configureTestingModule({
      imports: [PublicShareComponent],
      providers: [
        { provide: Router, useValue: mockRouter },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of({
              get: (key: string) => key === 'token' ? 'test-token' : null
            })
          }
        },
        { provide: ShareService, useValue: mockShareService },
        { provide: FileOperationsService, useValue: mockFileOps },
        { provide: MatDialog, useValue: mockDialog }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PublicShareComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should fetch folder contents when visiting a folder token', () => {
    expect(mockShareService.visitPublicLink).toHaveBeenCalledWith('test-token');
    expect(mockFileOps.getStorageContents).toHaveBeenCalledWith('test-folder-id');
    expect(component.isFile()).toBe(false);
  });

  it('should download a file when onDownloadItem is called for a file', () => {
    const item: any = { id: 'file-123', name: 'test.txt', itemType: 'file' };
    component.onDownloadItem(item);
    expect(mockFileOps.downloadFile).toHaveBeenCalledWith('file-123');
  });

  it('should normalize child item fields for the item cards', () => {
    const items = component.items();
    const folder: any = items.find((item) => item.itemType === 'folder');
    const file: any = items.find((item) => item.itemType === 'file');

    expect(folder).toMatchObject({
      name: 'Child folder',
      createdAt: '2026-09-01T10:00:00Z',
      updatedAt: '2026-09-02T10:00:00Z',
    });
    expect(file).toMatchObject({
      name: 'child.txt',
      sizeBytes: 2048,
      createdAt: '2026-09-01T10:00:00Z',
      updatedAt: '2026-09-02T10:00:00Z',
    });
  });

  it('should navigate to subfolder when onOpenItem is called for a folder', () => {
    const item: any = { id: 'folder-123', itemType: 'folder' };
    component.onOpenItem(item);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/public-share/folder', 'folder-123']);
  });
});
