import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { Drive } from './drive';

describe('Drive', () => {
  let component: Drive;
  let fixture: ComponentFixture<Drive>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        RouterTestingModule,
        Drive, // Standalone component imported directly
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Drive);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the drive dashboard component', () => {
    expect(component).toBeTruthy();
  });

  it('should default to the home tab on initialization', () => {
    expect(component.currentNav()).toBe('home');
  });

  it('should switch tabs correctly and update currentNav signal', () => {
    component.switchNav('recent');
    expect(component.currentNav()).toBe('recent');

    component.switchNav('home');
    expect(component.currentNav()).toBe('home');
  });

  it('should compute the correct storage usage percentage profile', () => {
    component.usedBytes.set(5);
    component.totalBytes.set(20 * 1024 ** 3);
    // (5 / 20) * 100 = 25%
    expect(component.storagePercentage()).toBe(25);
  });
});
