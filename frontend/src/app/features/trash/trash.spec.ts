import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Trash } from './trash';

describe('Trash', () => {
  let component: Trash;
  let fixture: ComponentFixture<Trash>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Trash],
    }).compileComponents();

    fixture = TestBed.createComponent(Trash);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
