import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DashboardHeader } from './dashboard-header';
import { provideRouter } from '@angular/router';
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('DashboardHeader', () => {
  let component: DashboardHeader;
  let fixture: ComponentFixture<DashboardHeader>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardHeader],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardHeader);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit searchChange on search input change', () => {
    const emitSpy = vi.spyOn(component.searchChange, 'emit');
    const inputElement = fixture.nativeElement.querySelector('input');

    inputElement.value = 'test search';
    inputElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith('test search');
  });
});
