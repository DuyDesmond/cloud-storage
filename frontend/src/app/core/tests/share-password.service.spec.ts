import { TestBed } from '@angular/core/testing';
import { SharePasswordService } from '../share/services/share-password.service';
import { describe, it, expect, beforeEach } from 'vitest';

describe('SharePasswordService', () => {
  let service: SharePasswordService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SharePasswordService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should set and get password', () => {
    service.setPassword('secret123');
    expect(service.getPassword()).toBe('secret123');
  });

  it('should clear password', () => {
    service.setPassword('secret123');
    service.clearPassword();
    expect(service.getPassword()).toBeNull();
  });
});
