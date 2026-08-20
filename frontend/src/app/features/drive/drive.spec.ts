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
});
