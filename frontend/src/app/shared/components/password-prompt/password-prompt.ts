import { Component, inject } from '@angular/core';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';

@Component({
  selector: 'app-password-prompt',
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIconModule,
    ReactiveFormsModule,
  ],
  templateUrl: './password-prompt.html',
  styleUrl: './password-prompt.scss',
})
export class PasswordPromptComponent {
  private dialogRef = inject(MatDialogRef<PasswordPromptComponent>);
  private fb = inject(FormBuilder);

  hidePassword = true;
  form = this.fb.group({
    password: ['', Validators.required],
  });

  submit() {
    if (this.form.valid) {
      this.dialogRef.close(this.form.value.password);
    }
  }

  cancel() {
    this.dialogRef.close(null);
  }
}
