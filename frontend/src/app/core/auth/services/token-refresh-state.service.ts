import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TokenRefreshStateService {
  isRefreshing = false;
  refreshTokenSubject = new BehaviorSubject<boolean | null>(null);
}
