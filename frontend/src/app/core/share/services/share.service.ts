import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface SharedUser {
  email: string;
  name: string;
  permission: 'view' | 'edit';
  has_password: boolean;
}

export interface PublicLinkState {
  enabled: boolean;
  permission: 'view' | 'edit';
  has_password: boolean;
  link: string | null;
}

export interface ShareState {
  public_link: PublicLinkState;
  users: SharedUser[];
}

@Injectable({ providedIn: 'root' })
export class ShareService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}${environment.apiStr}/share`;

  getShareState(targetId: string, isFile: boolean): Observable<ShareState> {
    return this.http.get<ShareState>(`${this.apiUrl}/state`, {
      params: { target_id: targetId, is_file: isFile },
      withCredentials: true,
    });
  }

  shareWithUser(
    targetId: string,
    isFile: boolean,
    email: string,
    permission: 'view' | 'edit',
    password?: string,
  ): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.apiUrl}/user`,
      {
        target_id: targetId,
        is_file: isFile,
        email,
        permission,
        password: password || null,
      },
      { withCredentials: true },
    );
  }

  revokeUserShare(
    targetId: string,
    isFile: boolean,
    email: string,
  ): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/user`, {
      body: { target_id: targetId, is_file: isFile, email },
      withCredentials: true,
    });
  }

  setPublicLink(
    targetId: string,
    isFile: boolean,
    enabled: boolean,
    permission: 'view' | 'edit',
    password?: string,
  ): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.apiUrl}/public`,
      {
        target_id: targetId,
        is_file: isFile,
        enabled,
        permission,
        password: password || null,
      },
      { withCredentials: true },
    );
  }

  visitPublicLink(shareToken: string): Observable<{
    message: string;
    is_file: boolean;
    target_id: string;
    file_name?: string;
    mime_type?: string;
    size_bytes?: number;
  }> {
    return this.http.post<{
      message: string;
      is_file: boolean;
      target_id: string;
      file_name?: string;
      mime_type?: string;
      size_bytes?: number;
    }>(`${this.apiUrl}/visit/${shareToken}`, {}, { withCredentials: true });
  }
}
