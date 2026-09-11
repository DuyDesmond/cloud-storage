import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { By } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import { ShareDialog } from './share-dialog';
import { ShareService } from '../../core/share/services/share.service';

describe('ShareDialog', () => {
  let component: ShareDialog;
  let fixture: ComponentFixture<ShareDialog>;
  let shareServiceSpy: any;
  let dialogRefSpy: any;

  const mockShareState = {
    users: [
      {
        name: 'John Doe',
        email: 'john@nephos.com',
        permission: 'view',
        has_password: true,
      },
    ],
    public_link: {
      enabled: true,
      permission: 'view',
      link: 'abc123xyz',
    },
  };

  beforeEach(async () => {
    shareServiceSpy = {
      getShareState: vi.fn().mockReturnValue(of(mockShareState)),
      shareWithUser: vi.fn().mockReturnValue(of({})),
      revokeUserShare: vi.fn().mockReturnValue(of({})),
      setPublicLink: vi.fn().mockReturnValue(of({})),
    };

    dialogRefSpy = {
      close: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ShareDialog],
      providers: [
        { provide: ShareService, useValue: shareServiceSpy },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            item: { id: 'item-1', name: 'Document.pdf', itemType: 'file' },
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ShareDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the dialog and load initial share state', () => {
    expect(component).toBeTruthy();
    expect(shareServiceSpy.getShareState).toHaveBeenCalledWith('item-1', true);
    expect(component.shareState()).toEqual(mockShareState);
    expect(component.isLoading()).toBe(false);
  });

  it('should display loading spinner when isLoading is true', () => {
    component.isLoading.set(true);
    fixture.detectChanges();

    const spinner = fixture.debugElement.query(By.css('mat-spinner'));
    expect(spinner).toBeTruthy();
  });

  it('should add a user share successfully when form is valid', () => {
    component.shareUserForm.patchValue({
      email: 'newuser@nephos.com',
      permission: 'edit',
      password: 'securepassword',
    });

    component.addUserShare();

    expect(shareServiceSpy.shareWithUser).toHaveBeenCalledWith(
      'item-1',
      true,
      'newuser@nephos.com',
      'edit',
      'securepassword',
    );
  });

  it('should revoke a user share when requested', () => {
    const testUser = mockShareState.users[0] as any;
    component.removeUserShare(testUser);

    expect(shareServiceSpy.revokeUserShare).toHaveBeenCalledWith(
      'item-1',
      true,
      'john@nephos.com',
    );
  });

  it('should copy public link to clipboard', () => {
    const writeTextSpy = vi.fn();
    vi.stubGlobal('navigator', {
      clipboard: { writeText: writeTextSpy },
    });
    vi.stubGlobal('window', {
      location: { origin: 'https://nephos.app' },
    });

    component.copyLink();

    expect(writeTextSpy).toHaveBeenCalledWith(
      'https://nephos.app/shared/abc123xyz',
    );

    vi.unstubAllGlobals();
  });

  it('should close the dialog when done button is invoked', () => {
    component.close();
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });
});
