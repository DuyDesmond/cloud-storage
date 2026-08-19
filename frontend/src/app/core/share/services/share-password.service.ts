import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class SharePasswordService {
  private activePassword: string | null = null;

  setPassword(password: string) {
    this.activePassword = password;
  }

  getPassword(): string | null {
    return this.activePassword;
  }

  clearPassword() {
    this.activePassword = null;
  }
}
