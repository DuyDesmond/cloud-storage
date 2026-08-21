import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { By } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import { Register } from './register';
import { AuthService } from '@core/auth/services/auth.service';

describe('Register', () => {
  let component: Register;
  let fixture: ComponentFixture<Register>;

  let authServiceSpy: { register: ReturnType<typeof vi.fn> };
  let routerSpy: { navigate: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    authServiceSpy = { register: vi.fn() };
    routerSpy = { navigate: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [Register],
      providers: [
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Router, useValue: routerSpy },
        { provide: ActivatedRoute, useValue: {} }
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Register);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should invalidate the form when empty', () => {
    expect(component.registerForm.valid).toBe(false);
  });

  it('should enforce password mismatch validation', () => {
    component.registerForm.patchValue({
      password: 'password123',
      confirmPassword: 'differentPassword'
    });

    // Trigger the cross-field validator
    component.registerForm.updateValueAndValidity();

    expect(component.registerForm.get('confirmPassword')?.hasError('passwordMismatch')).toBe(true);
  });

  it('should correctly evaluate the isFormReady getter', () => {
    expect(component.isFormReady()).toBe(false);

    component.registerForm.patchValue({
      username: 'Jane Doe',
      email: 'jane@nephos.com',
      password: 'password123',
      confirmPassword: 'password123',
      terms: true
    });

    expect(component.isFormReady()).toBe(true);
  });

  it('should toggle password and confirm password visibility', () => {
    expect(component.showPassword).toBe(false);
    expect(component.showConfirmPassword).toBe(false);

    component.togglePassword();
    component.toggleConfirmPassword();

    expect(component.showPassword).toBe(true);
    expect(component.showConfirmPassword).toBe(true);
  });

  it('should mark form as touched if invalid on submit', () => {
    const markAllAsTouchedSpy = vi.spyOn(component.registerForm, 'markAllAsTouched');
    component.onSubmit();

    expect(markAllAsTouchedSpy).toHaveBeenCalled();
    expect(authServiceSpy.register).not.toHaveBeenCalled();
  });

  it('should navigate to /login on successful registration', () => {
    authServiceSpy.register.mockReturnValue(of({ email: 'jane@nephos.com' }));

    component.registerForm.patchValue({
      username: 'Jane Doe',
      email: 'jane@nephos.com',
      password: 'password123',
      confirmPassword: 'password123',
      terms: true
    });

    component.onSubmit();

    expect(component.isLoading()).toBe(false);
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('should display error message on registration failure', () => {
    authServiceSpy.register.mockReturnValue(throwError(() => new Error('Registration failed')));

    component.registerForm.patchValue({
      username: 'Jane Doe',
      email: 'jane@nephos.com',
      password: 'password123',
      confirmPassword: 'password123',
      terms: true
    });

    component.onSubmit();

    expect(component.isLoading()).toBe(false);
    expect(component.errorMessage()).toBe('Registration failed. Please check your credentials or network connections.');
  });

  // --- DOM Rendering Tests ---

  it('should render the error banner if errorMessage signal is set', () => {
    const testError = 'Custom registration error.';
    component.errorMessage.set(testError);
    fixture.detectChanges();

    const banner = fixture.debugElement.query(By.css('.alert-banner'));
    expect(banner).toBeTruthy();
    expect(banner.nativeElement.textContent).toContain(testError);
  });

  it('should show the loading spinner when isLoading signal is true', () => {
    component.isLoading.set(true);
    fixture.detectChanges();

    const spinner = fixture.debugElement.query(By.css('mat-spinner'));
    expect(spinner).toBeTruthy();
  });

  // --- Edge Case & DOM Interaction Tests ---

  it('should reject whitespace-only strings in the isFormReady getter', () => {
    component.registerForm.patchValue({
      username: '   ', // Just spaces
      email: '  @nephos.com',
      password: 'password123',
      confirmPassword: 'password123',
      terms: true
    });

    // Even if the reactive form considers it valid, our getter should catch the empty trim
    expect(component.isFormReady()).toBe(false);
  });

  it('should clear the passwordMismatch error when passwords are corrected', () => {
    // 1. Induce the mismatch error
    component.registerForm.patchValue({
      password: 'password123',
      confirmPassword: 'wrongPassword'
    });
    component.registerForm.updateValueAndValidity();
    expect(component.registerForm.get('confirmPassword')?.hasError('passwordMismatch')).toBe(true);

    // 2. Correct the mismatch
    component.registerForm.patchValue({ confirmPassword: 'password123' });
    component.registerForm.updateValueAndValidity();

    // 3. Verify it clears
    expect(component.registerForm.get('confirmPassword')?.hasError('passwordMismatch')).toBe(false);
  });

  it('should disable the submit button when the form is incomplete or loading', () => {
    fixture.detectChanges();
    const submitButton = fixture.debugElement.query(By.css('.submit-button')).nativeElement;

    // Initially disabled because form is empty
    expect(submitButton.disabled).toBe(true);

    // Fill the form correctly
    component.registerForm.patchValue({
      username: 'Jane Doe',
      email: 'jane@nephos.com',
      password: 'password123',
      confirmPassword: 'password123',
      terms: true
    });
    fixture.detectChanges();

    // Should now be enabled
    expect(submitButton.disabled).toBe(false);

    // Should disable again if loading signal emits true
    component.isLoading.set(true);
    fixture.detectChanges();
    expect(submitButton.disabled).toBe(true);
  });

  it('should reflect DOM checkbox interactions in the form control', async () => {
    fixture.detectChanges();

    // Angular Material checkboxes use a nested input for the actual click target
    const checkboxInput = fixture.debugElement.query(By.css('mat-checkbox input')).nativeElement;

    expect(component.registerForm.get('terms')?.value).toBe(false);

    // Simulate a physical click
    checkboxInput.click();
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.registerForm.get('terms')?.value).toBe(true);
  });
});
