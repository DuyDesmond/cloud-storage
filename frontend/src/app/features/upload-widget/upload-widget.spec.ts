import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UploadWidget } from './upload-widget';

describe('UploadWidget', () => {
  let component: UploadWidget;
  let fixture: ComponentFixture<UploadWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadWidget]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UploadWidget);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
