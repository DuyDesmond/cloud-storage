import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class LoggerService {
  private currentCorrelationId: string | null = null;

  setCorrelationId(id: string) {
    this.currentCorrelationId = id;
  }

  log(message: string, ...optionalParams: any[]) {
    console.log(this.formatMessage('INFO', message), ...optionalParams);
  }

  error(message: string, ...optionalParams: any[]) {
    console.error(this.formatMessage('ERROR', message), ...optionalParams);
  }

  warn(message: string, ...optionalParams: any[]) {
    console.warn(this.formatMessage('WARN', message), ...optionalParams);
  }

  private formatMessage(level: string, message: string): string {
    const timestamp = new Date().toISOString();
    const correlation = this.currentCorrelationId
      ? ` [${this.currentCorrelationId}]`
      : '';
    return `${timestamp} ${level}${correlation}: ${message}`;
  }
}
