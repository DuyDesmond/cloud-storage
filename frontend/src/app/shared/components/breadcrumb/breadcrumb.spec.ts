import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Breadcrumb } from './breadcrumb';
import { provideRouter } from '@angular/router';
import { ComponentRef } from '@angular/core';
import { describe, it, expect, beforeEach } from 'vitest';

describe('Breadcrumb', () => {
  let component: Breadcrumb;
  let fixture: ComponentFixture<Breadcrumb>;
  let componentRef: ComponentRef<Breadcrumb>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Breadcrumb],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(Breadcrumb);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should compute homeLink correctly based on section', () => {
    componentRef.setInput('section', 'drive');
    fixture.detectChanges();
    expect(component.homeLink()).toBe('/drive/root');

    componentRef.setInput('section', 'shared-with-me');
    fixture.detectChanges();
    expect(component.homeLink()).toBe('/drive/shared-with-me');

    componentRef.setInput('section', 'trash');
    fixture.detectChanges();
    expect(component.homeLink()).toBe('/trash');
  });

  it('should compute homeIcon correctly based on section', () => {
    componentRef.setInput('section', 'drive');
    fixture.detectChanges();
    expect(component.homeIcon()).toBe('home');

    componentRef.setInput('section', 'shared-with-me');
    fixture.detectChanges();
    expect(component.homeIcon()).toBe('group');

    componentRef.setInput('section', 'trash');
    fixture.detectChanges();
    expect(component.homeIcon()).toBe('delete');
  });
});
