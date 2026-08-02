import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { of } from 'rxjs';

import { Register } from './register';
import { AuthService } from '@core/auth/services/auth.service';

describe('Register', () => {
  let component: Register;
  let fixture: ComponentFixture<Register>;

  const mockAuthService = {
    register: () => of({ success: true }),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Register, RouterTestingModule],
      providers: [{ provide: AuthService, useValue: mockAuthService }],
    }).compileComponents();

    fixture = TestBed.createComponent(Register);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
