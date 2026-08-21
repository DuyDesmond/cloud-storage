import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, ActivatedRoute, Router } from '@angular/router';
import { SharedLinkComponent } from './shared-link';
import { AuthService } from '../../core/auth/services/auth.service';
import { ShareService } from '../../core/share/services/share.service';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { signal } from '@angular/core';

describe('SharedLinkComponent', () => {
  let component: SharedLinkComponent;
  let fixture: ComponentFixture<SharedLinkComponent>;
  let mockAuthService: any;
  let mockShareService: any;
  let mockRouter: any;

  beforeEach(async () => {
    mockAuthService = {
      currentUser: signal({ full_name: 'Test', email: 'test@test.com' }),
      getProfile: vi.fn().mockReturnValue(of({ full_name: 'Test', email: 'test@test.com' }))
    };

    mockShareService = {
      visitPublicLink: vi.fn().mockReturnValue(of({ is_file: true }))
    };

    mockRouter = {
      navigate: vi.fn()
    };

    await TestBed.configureTestingModule({
      imports: [SharedLinkComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: mockAuthService },
        { provide: ShareService, useValue: mockShareService },
        { provide: Router, useValue: mockRouter },
        { 
          provide: ActivatedRoute, 
          useValue: { snapshot: { paramMap: { get: () => 'fake-token' } } } 
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SharedLinkComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
