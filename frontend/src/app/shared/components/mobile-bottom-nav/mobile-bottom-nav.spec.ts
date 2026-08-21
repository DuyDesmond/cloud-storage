import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MobileBottomNav } from './mobile-bottom-nav';
import { provideRouter, Router } from '@angular/router';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { SidePanelNavItem } from '../side-panel/side-panel';

describe('MobileBottomNav', () => {
  let component: MobileBottomNav;
  let fixture: ComponentFixture<MobileBottomNav>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MobileBottomNav],
      providers: [provideRouter([])]
    }).compileComponents();

    fixture = TestBed.createComponent(MobileBottomNav);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit navChange and navigate on nav click', () => {
    const emitSpy = vi.spyOn(component.navChange, 'emit');
    const navigateSpy = vi.spyOn(router, 'navigateByUrl');
    const testItem: SidePanelNavItem = { key: 'home', icon: 'home', label: 'Home', route: '/drive/root' };
    
    component.onNavClick(testItem);
    
    expect(emitSpy).toHaveBeenCalledWith('home');
    expect(navigateSpy).toHaveBeenCalledWith('/drive/root');
  });

  it('should emit upload event on upload button click', () => {
    const emitSpy = vi.spyOn(component.upload, 'emit');
    const uploadBtn = fixture.nativeElement.querySelector('.upload-tab');
    
    uploadBtn.click();
    
    expect(emitSpy).toHaveBeenCalled();
  });
});
