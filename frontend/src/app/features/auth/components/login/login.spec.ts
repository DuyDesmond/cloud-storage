import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { By } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import { Login } from './login';
import { AuthService } from '@core/auth/services/auth.service';

describe('Login', () => {
  let component: Login;
  let fixture: ComponentFixture<Login>;

  let authServiceSpy: { login: ReturnType<typeof vi.fn> };
  let routerSpy: { navigate: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    authServiceSpy = { login: vi.fn() };
    routerSpy = { navigate: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Router, useValue: routerSpy },
        { provide: ActivatedRoute, useValue: {} },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Login);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should toggle password visibility', () => {
    expect(component.showPassword).toBe(false);
    component.togglePassword();
    expect(component.showPassword).toBe(true);
  });

  it('should mark all controls as touched if form is invalid on submit', () => {
    const markAllAsTouchedSpy = vi.spyOn(
      component.loginForm,
      'markAllAsTouched',
    );
    component.onSubmit();

    expect(markAllAsTouchedSpy).toHaveBeenCalled();
    expect(authServiceSpy.login).not.toHaveBeenCalled();
  });

  it('should navigate to /drive on successful login', () => {
    authServiceSpy.login.mockReturnValue(of({ email: 'test@nephos.com' }));

    component.loginForm.patchValue({
      email: 'test@nephos.com',
      password: 'password123',
    });

    component.onSubmit();

    expect(component.isLoading()).toBe(false);
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/drive']);
  });

  it('should set an error message signal on failed login', () => {
    authServiceSpy.login.mockReturnValue(
      throwError(() => new Error('Auth failed')),
    );

    component.loginForm.patchValue({
      email: 'test@nephos.com',
      password: 'password123',
    });

    component.onSubmit();

    expect(component.isLoading()).toBe(false);
    expect(component.errorMessage()).toBe(
      'Invalid email or password. Please try again.',
    );
  });

  // --- New DOM Rendering Tests ---

  it('should display the error banner when errorMessage signal is set', () => {
    const testError = 'Invalid email or password. Please try again.';
    component.errorMessage.set(testError);
    fixture.detectChanges(); // Trigger change detection to update the DOM

    const errorBanner = fixture.debugElement.query(By.css('.error-banner'));
    expect(errorBanner).toBeTruthy();
    expect(errorBanner.nativeElement.textContent).toContain(testError);
  });

  it('should render the loading spinner and "Signing In..." text when isLoading signal is true', () => {
    component.isLoading.set(true);
    fixture.detectChanges();

    const spinner = fixture.debugElement.query(By.css('mat-spinner'));
    const buttonContent = fixture.debugElement.query(
      By.css('.button-content'),
    ).nativeElement;

    expect(spinner).toBeTruthy();
    expect(buttonContent.textContent).toContain('Signing In...');
  });
});
