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
        folders: [],
        files: []
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

  it('should navigate to subfolder when onOpenItem is called for a folder', () => {
    const item: any = { id: 'folder-123', itemType: 'folder' };
    component.onOpenItem(item);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/shared/folder', 'folder-123']);
  });
});
