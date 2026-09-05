import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DriveItemCard } from './drive-item-card';
import { ComponentRef } from '@angular/core';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DriveItem } from './drive-item.model';

describe('DriveItemCard', () => {
  let component: DriveItemCard;
  let fixture: ComponentFixture<DriveItemCard>;
  let componentRef: ComponentRef<DriveItemCard>;

  const mockItem: DriveItem = {
    id: '1',
    name: 'Test File',
    itemType: 'file',
    sizeBytes: 1024,
    updatedAt: new Date().toISOString(),
    createdAt: new Date().toISOString(),
    mimeType: 'text/plain',
    ownerId: 'user1',
    parentFolderId: 'root',
    path: 'root',
    isTrashed: false,
    trashedAt: null,
    storageKey: 'test-key',
    contentHash: 'hash',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DriveItemCard],
    }).compileComponents();

    fixture = TestBed.createComponent(DriveItemCard);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    componentRef.setInput('item', mockItem);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should compute displayMeta correctly for files', () => {
    expect(component.displayMeta()).toBe('1 KB');
  });

  it('should compute iconName correctly for files', () => {
    expect(component.iconName()).toBe('description');
  });

  it('should emit open event on card click', () => {
    const emitSpy = vi.spyOn(component.open, 'emit');
    component.onCardClick();
    expect(emitSpy).toHaveBeenCalledWith(mockItem);
  });

  it('should emit download event', () => {
    const emitSpy = vi.spyOn(component.download, 'emit');
    const mockEvent = new MouseEvent('click');
    mockEvent.stopPropagation = vi.fn();
    component.onDownload(mockEvent);
    expect(emitSpy).toHaveBeenCalledWith(mockItem);
    expect(mockEvent.stopPropagation).toHaveBeenCalled();
  });
});
