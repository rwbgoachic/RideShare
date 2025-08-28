import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';
import { PricingController } from './controllers/pricing.controller';
import { ReservationsController } from './controllers/reservations.controller';
import { AirportController } from './controllers/airport.controller';
import { DriverController } from './controllers/driver.controller';
import { PricingService } from './services/pricing.service';
import { ReservationsService } from './services/reservations.service';
import { AirportService } from './services/airport.service';
import { DriverService } from './services/driver.service';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    HttpModule,
  ],
  controllers: [
    PricingController,
    ReservationsController,
    AirportController,
    DriverController,
  ],
  providers: [
    PricingService,
    ReservationsService,
    AirportService,
    DriverService,
  ],
})
export class AppModule {}