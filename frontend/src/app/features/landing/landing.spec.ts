import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { By } from '@angular/platform-browser';
import { describe, it, expect, beforeEach } from 'vitest';

import { Landing } from './landing';

describe('Landing Component', () => {
  let component: Landing;
  let fixture: ComponentFixture<Landing>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Landing],
      providers: [
        // Provide mock routing context for the RouterLink directives
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Landing);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should render the main headline', () => {
    const headline = fixture.debugElement.query(By.css('h1')).nativeElement;
    expect(headline.textContent).toContain('Cloud Storage, as light as air.');
  });

  it('should render the sign-in link with the correct route', () => {
    const signinLink = fixture.debugElement.query(
      By.css('a[routerLink="/login"]'),
    );

    expect(signinLink).toBeTruthy();
    expect(signinLink.nativeElement.textContent).toContain('Sign in');
  });

  it('should render multiple registration links with the correct route', () => {
    // The template contains one in the header and one in the main CTA
    const registerLinks = fixture.debugElement.queryAll(
      By.css('a[routerLink="/register"]'),
    );

    expect(registerLinks.length).toBe(2);
    expect(registerLinks[0].nativeElement.textContent).toContain(
      'Create account',
    );
    expect(registerLinks[1].nativeElement.textContent).toContain(
      'Start for Free',
    );
  });
});
