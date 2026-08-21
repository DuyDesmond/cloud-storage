import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PasswordPromptComponent } from './password-prompt';
import { MatDialogRef } from '@angular/material/dialog';
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('PasswordPromptComponent', () => {
  let component: PasswordPromptComponent;
  let fixture: ComponentFixture<PasswordPromptComponent>;
  let mockDialogRef: any;

  beforeEach(async () => {
    mockDialogRef = {
      close: vi.fn()
    };

    await TestBed.configureTestingModule({
      imports: [PasswordPromptComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(PasswordPromptComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should close dialog with password on valid submit', () => {
    component.form.controls.password.setValue('testpass');
    component.submit();
    expect(mockDialogRef.close).toHaveBeenCalledWith('testpass');
  });

  it('should not close dialog on invalid submit', () => {
    component.form.controls.password.setValue('');
    component.submit();
    expect(mockDialogRef.close).not.toHaveBeenCalled();
  });

  it('should close dialog with null on cancel', () => {
    component.cancel();
    expect(mockDialogRef.close).toHaveBeenCalledWith(null);
  });
});
