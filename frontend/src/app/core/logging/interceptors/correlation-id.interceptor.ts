import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { LoggerService } from '../../logging/services/logger.service';

export const correlationIdInterceptor: HttpInterceptorFn = (req, next) => {
  const logger = inject(LoggerService);
  const correlationId = crypto.randomUUID();

  const modifiedReq = req.clone({
    headers: req.headers.set('X-Correlation-ID', correlationId),
  });

  logger.setCorrelationId(correlationId);
  logger.log(`HTTP ${req.method} ${req.url}`);

  return next(modifiedReq);
};
