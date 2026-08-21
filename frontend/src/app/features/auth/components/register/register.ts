import { Component, inject, signal, computed, DestroyRef } from '@angular/core';

import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '@core/auth/services/auth.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';

import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';

export const passwordMatchValidator: ValidatorFn = (
  control: AbstractControl,
): ValidationErrors | null => {
  const password = control.get('password');
  const confirmPassword = control.get('confirmPassword');

  if (password && confirmPassword && password.value !== confirmPassword.value) {
    confirmPassword.setErrors({ passwordMismatch: true });
    return { passwordMismatch: true };
  } else if (confirmPassword?.hasError('passwordMismatch')) {
    confirmPassword.setErrors(null);
  }

  return null;
};

@Component({
  selector: 'app-register',
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './register.html',
  styleUrl: './register.scss',
})
export class Register {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  registerForm = this.fb.group(
    {
      username: ['', [Validators.required, Validators.minLength(3)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]],
      terms: [false, [Validators.requiredTrue]],
    },
    { validators: passwordMatchValidator },
  );

  private formValues = toSignal(this.registerForm.valueChanges);
  private formStatus = toSignal(this.registerForm.statusChanges);

  isFormReady = computed(() => {
    const values = this.formValues() || this.registerForm.value;
    const status = this.formStatus() || this.registerForm.status;

    const { username, email, password, confirmPassword, terms } = values;

    const allFieldsFilled =
      Boolean(username?.trim()) &&
      Boolean(email?.trim()) &&
      Boolean(password) &&
      Boolean(confirmPassword);

    const passwordsMatch =
      !!password &&
      !!confirmPassword &&
      password === confirmPassword &&
      password.length >= 6;

    const termsAccepted = Boolean(terms);

    return (
      allFieldsFilled &&
      passwordsMatch &&
      termsAccepted &&
      status === 'VALID'
    );
  });

  showPassword = false;
  showConfirmPassword = false;
  isLoading = signal(false);
  errorMessage = signal<string | null>(null);

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  toggleConfirmPassword(): void {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  onSubmit(): void {
    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const { username, email, password } = this.registerForm.getRawValue();

    if (!username || !email || !password) return;

    this.authService.register(username, email, password)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (user) => {
          this.isLoading.set(false);
          if (user && user.email) {
            this.router.navigate(['/login']);
          }
        },
        error: () => {
          this.isLoading.set(false);
          this.errorMessage.set(
            'Registration failed. Please check your credentials or network connections.',
          );
        },
      });
  }
}
