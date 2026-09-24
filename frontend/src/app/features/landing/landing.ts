import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NgOptimizedImage } from '@angular/common';

@Component({
  selector: 'app-landing',
  imports: [CommonModule, RouterLink, MatButtonModule, MatIconModule, NgOptimizedImage],
  templateUrl: './landing.html',
  styleUrls: ['./landing.scss'],
})
export class Landing {}
