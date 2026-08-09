import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DriveItemCard } from './drive-item-card';
import { DriveItem } from './drive-item.model';

describe('DriveItem', () => {
  let component: DriveItemCard;
  let fixture: ComponentFixture<DriveItemCard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DriveItemCard],
    }).compileComponents();

    fixture = TestBed.createComponent(DriveItemCard);
    component = fixture.componentInstance;
    const mockItem: DriveItem = {
      id: 'f101',
      ownerId: 'u1',
      parentFolderId: null,
      path: 'root',
      name: 'Q4 Market Report.pdf',
      itemType: 'file',
      storageKey: 'users/u1/q4_report.pdf',
      sizeBytes: 1258291,
      mimeType: 'application/pdf',
      contentHash: null,
      isTrashed: false,
      trashedAt: null,
      createdAt: '2023-10-22T15:15:00Z',
      updatedAt: '2023-10-22T15:15:00Z',
    };

    fixture.componentRef.setInput('item', mockItem);
    fixture.detectChanges();

    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
