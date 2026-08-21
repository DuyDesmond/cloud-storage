import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SidePanel } from './side-panel';
import { provideRouter, Router } from '@angular/router';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { StorageStateService } from '../../../core/file-operations/services/storage-state.service';
import { signal } from '@angular/core';

describe('SidePanel', () => {
  let component: SidePanel;
  let fixture: ComponentFixture<SidePanel>;
  let router: Router;
  let mockStorageState: any;

  beforeEach(async () => {
    mockStorageState = {
      isLoading: signal(false),
      usedStorageGB: signal(1.5),
      totalStorageGB: signal(15),
      storagePercentage: signal(10)
    };

    await TestBed.configureTestingModule({
      imports: [SidePanel],
      providers: [
        provideRouter([]),
        { provide: StorageStateService, useValue: mockStorageState }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SidePanel);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should toggle collapse state', () => {
    expect(component.isCollapsed()).toBe(false);
    component.toggleCollapse();
    expect(component.isCollapsed()).toBe(true);
  });

  it('should emit navChange and navigate on nav click', () => {
    const emitSpy = vi.spyOn(component.navChange, 'emit');
    const navigateSpy = vi.spyOn(router, 'navigateByUrl');
    
    component.onNavClick(component.navItems[0]); // Home
    
    expect(emitSpy).toHaveBeenCalledWith('home');
    expect(navigateSpy).toHaveBeenCalledWith('/drive/root');
  });

  it('should emit upload event', () => {
    const emitSpy = vi.spyOn(component.upload, 'emit');
    const uploadBtn = fixture.nativeElement.querySelector('.upload-btn');
    uploadBtn.click();
    expect(emitSpy).toHaveBeenCalled();
  });

  it('should emit upgrade event', () => {
    const emitSpy = vi.spyOn(component.upgrade, 'emit');
    const upgradeBtn = fixture.nativeElement.querySelector('.upgrade-btn');
    upgradeBtn.click();
    expect(emitSpy).toHaveBeenCalled();
  });
});
