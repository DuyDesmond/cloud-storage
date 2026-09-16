import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { UploadDialog } from './upload-dialog';

describe('UploadDialog', () => {
  let component: UploadDialog;
  let fixture: ComponentFixture<UploadDialog>;

  // Mock implementation of MatDialogRef
  const mockDialogRef = {
    close: vi.fn(), // Use jest.fn() or vi.fn() if using Jest/Vitest
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadDialog],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {} },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadDialog);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
