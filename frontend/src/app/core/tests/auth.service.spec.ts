import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AuthService, User } from '../auth/services/auth.service';
import { AUTH_ENDPOINTS } from '../auth/endpoints/auth-endpoints';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  const mockUser: User = {
    id: '123',
    email: 'test@example.com',
    full_name: 'Test User',
    created_at: new Date().toISOString()
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should login and set current user', () => {
    service.login('test@example.com', 'password').subscribe(user => {
      expect(user).toEqual(mockUser);
      expect(service.currentUser()).toEqual(mockUser);
    });

    const req = httpMock.expectOne(AUTH_ENDPOINTS.login);
    expect(req.request.method).toBe('POST');
    req.flush(mockUser);
  });

  it('should clear current user on logout', () => {
    // Set initial user
    service.currentUser.set(mockUser);
    
    service.logout().subscribe(res => {
      expect(res.message).toBe('Logged out');
      expect(service.currentUser()).toBeNull();
    });

    const req = httpMock.expectOne(AUTH_ENDPOINTS.logout);
    expect(req.request.method).toBe('POST');
    req.flush({ message: 'Logged out' });
  });
});
