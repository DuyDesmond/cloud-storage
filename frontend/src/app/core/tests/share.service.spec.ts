import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ShareService } from '../share/services/share.service';
import { environment } from '../../../environments/environment';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('ShareService', () => {
  let service: ShareService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ShareService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(ShareService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should get share state', () => {
    service.getShareState('item-1', true).subscribe(res => {
      expect(res).toBeTruthy();
    });

    const req = httpMock.expectOne(request => request.url === `${environment.apiUrl}${environment.apiStr}/share/state` && request.params.get('target_id') === 'item-1' && request.params.get('is_file') === 'true');
    expect(req.request.method).toBe('GET');
    req.flush({ public_link: {}, users: [] });
  });

  it('should share with user', () => {
    service.shareWithUser('item-1', true, 'test@example.com', 'view').subscribe(res => {
      expect(res.message).toBe('Success');
    });

    const req = httpMock.expectOne(`${environment.apiUrl}${environment.apiStr}/share/user`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ target_id: 'item-1', is_file: true, email: 'test@example.com', permission: 'view', password: null });
    req.flush({ message: 'Success' });
  });

  it('should revoke user share', () => {
    service.revokeUserShare('item-1', true, 'test@example.com').subscribe(res => {
      expect(res.message).toBe('Success');
    });

    const req = httpMock.expectOne(`${environment.apiUrl}${environment.apiStr}/share/user`);
    expect(req.request.method).toBe('DELETE');
    expect(req.request.body).toEqual({ target_id: 'item-1', is_file: true, email: 'test@example.com' });
    req.flush({ message: 'Success' });
  });

  it('should set public link', () => {
    service.setPublicLink('item-1', true, true, 'edit').subscribe(res => {
      expect(res.message).toBe('Success');
    });

    const req = httpMock.expectOne(`${environment.apiUrl}${environment.apiStr}/share/public`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ target_id: 'item-1', is_file: true, enabled: true, permission: 'edit', password: null });
    req.flush({ message: 'Success' });
  });
});
