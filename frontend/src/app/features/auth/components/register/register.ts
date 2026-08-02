import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '@core/auth/services/auth.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

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
  standalone: true,
  imports: [
    CommonModule,
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
  styleUrls: ['./register.scss'],
})
export class Register {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);

  registerForm: FormGroup = this.fb.group(
    {
      username: ['', [Validators.required, Validators.minLength(3)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]],
      terms: [false, [Validators.requiredTrue]],
    },
    { validators: passwordMatchValidator },
  );

  get isFormReady(): boolean {
    const { username, email, password, confirmPassword, terms } =
      this.registerForm.value;

    const allFieldsFilled =
      Boolean(username?.trim()) &&
      Boolean(email?.trim()) &&
      Boolean(password) &&
      Boolean(confirmPassword);

    const passwordsMatch = password === confirmPassword && password.length >= 6;

    const termsAccepted = Boolean(terms);

    return (
      allFieldsFilled &&
      passwordsMatch &&
      termsAccepted &&
      this.registerForm.valid
    );
  }

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

    const { username, email, password } = this.registerForm.value;

    this.authService.register(username, email, password).subscribe({
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
