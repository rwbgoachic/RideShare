import { Injectable, NotFoundException, UnauthorizedException } from '@nestjs/common';
import {
  DriverAuthDto,
  DriverRegistrationDto,
  DriverProfileDto,
  DriverStatusUpdateDto,
  LocationUpdateDto,
  RideOfferDto,
  RideOfferResponseDto,
  EarningsDto,
  TripHistoryDto,
  DriverStatus,
} from '../dto/driver.dto';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class DriverService {
  // Mock data store (in production, this would be database operations)
  private drivers = new Map();
  private currentOffers = new Map();
  private driverLocations = new Map();

  constructor() {
    // Initialize with mock driver data
    this.initializeMockData();
  }

  private initializeMockData() {
    const mockDriver = {
      id: 'mock-driver-id',
      firstName: 'John',
      lastName: 'Doe',
      email: 'john.doe@luxride.com',
      phone: '+1-312-555-0123',
      address: '123 Main St, Chicago, IL 60601',
      rating: 4.92,
      totalTrips: 1247,
      status: DriverStatus.OFFLINE,
      isActive: true,
      vehicle: {
        id: 'mock-vehicle-id',
        make: 'BMW',
        model: '5 Series',
        year: 2023,
        color: 'Black',
        licensePlate: 'LUX-123',
        category: 'black_sedan',
        photoUrls: [],
      },
    };

    this.drivers.set('mock-driver-id', mockDriver);
  }

  async login(loginDto: DriverAuthDto) {
    // Mock authentication - in production, verify against database
    if (loginDto.email === 'john.doe@luxride.com' && loginDto.password === 'password') {
      const driver = this.drivers.get('mock-driver-id');
      return {
        success: true,
        token: 'mock-jwt-token',
        driver: {
          id: driver.id,
          firstName: driver.firstName,
          lastName: driver.lastName,
          email: driver.email,
        },
      };
    }

    throw new UnauthorizedException('Invalid credentials');
  }

  async register(registrationDto: DriverRegistrationDto) {
    // Mock registration - in production, create new driver in database
    const driverId = uuidv4();
    const newDriver = {
      id: driverId,
      firstName: registrationDto.firstName,
      lastName: registrationDto.lastName,
      email: registrationDto.email,
      phone: registrationDto.phone,
      address: registrationDto.address,
      rating: 0,
      totalTrips: 0,
      status: DriverStatus.OFFLINE,
      isActive: false, // Requires onboarding completion
    };

    this.drivers.set(driverId, newDriver);

    return {
      success: true,
      driverId,
      message: 'Registration successful. Please complete onboarding.',
    };
  }

  async getProfile(driverId: string): Promise<DriverProfileDto> {
    const driver = this.drivers.get(driverId);
    if (!driver) {
      throw new NotFoundException('Driver not found');
    }

    const currentLocation = this.driverLocations.get(driverId);

    return {
      ...driver,
      currentLocation,
    };
  }

  async updateProfile(driverId: string, profileData: Partial<DriverProfileDto>) {
    const driver = this.drivers.get(driverId);
    if (!driver) {
      throw new NotFoundException('Driver not found');
    }

    // Update allowed fields
    const updatedDriver = {
      ...driver,
      firstName: profileData.firstName || driver.firstName,
      lastName: profileData.lastName || driver.lastName,
      phone: profileData.phone || driver.phone,
      address: profileData.address || driver.address,
    };

    this.drivers.set(driverId, updatedDriver);

    return {
      success: true,
      driver: updatedDriver,
    };
  }

  async updateStatus(driverId: string, statusUpdate: DriverStatusUpdateDto) {
    const driver = this.drivers.get(driverId);
    if (!driver) {
      throw new NotFoundException('Driver not found');
    }

    driver.status = statusUpdate.status;
    this.drivers.set(driverId, driver);

    if (statusUpdate.location) {
      this.driverLocations.set(driverId, statusUpdate.location);
    }

    // If going online, potentially send ride offers
    if (statusUpdate.status === DriverStatus.ONLINE) {
      this.simulateRideOffer(driverId);
    }

    return {
      success: true,
      status: driver.status,
      message: `Driver status updated to ${statusUpdate.status}`,
    };
  }

  async updateLocation(driverId: string, location: LocationUpdateDto) {
    this.driverLocations.set(driverId, {
      ...location,
      updatedAt: new Date().toISOString(),
    });

    return {
      success: true,
      message: 'Location updated successfully',
    };
  }

  async getCurrentOffer(driverId: string): Promise<RideOfferDto | null> {
    return this.currentOffers.get(driverId) || null;
  }

  async respondToOffer(driverId: string, offerId: string, response: RideOfferResponseDto) {
    const offer = this.currentOffers.get(driverId);
    
    if (!offer || offer.offerId !== offerId) {
      throw new NotFoundException('Offer not found or expired');
    }

    // Remove the offer
    this.currentOffers.delete(driverId);

    if (response.accepted) {
      // Update driver status to busy
      const driver = this.drivers.get(driverId);
      if (driver) {
        driver.status = DriverStatus.EN_ROUTE_PICKUP;
        this.drivers.set(driverId, driver);
      }

      return {
        success: true,
        message: 'Offer accepted. Navigate to pickup location.',
        tripId: offer.tripId,
      };
    } else {
      return {
        success: true,
        message: 'Offer declined.',
      };
    }
  }

  async getEarnings(driverId: string, period: string): Promise<EarningsDto> {
    // Mock earnings data
    const earningsData = {
      today: { gross: 15420, net: 12336, trips: 12, hours: 8.5, commission: 3084 },
      week: { gross: 89750, net: 71800, trips: 67, hours: 42.5, commission: 17950 },
      month: { gross: 387500, net: 310000, trips: 289, hours: 185, commission: 77500 },
      year: { gross: 4650000, net: 3720000, trips: 3467, hours: 2220, commission: 930000 },
    };

    const data = earningsData[period] || earningsData.week;

    return {
      period,
      grossEarnings: data.gross,
      netEarnings: data.net,
      totalTrips: data.trips,
      onlineHours: data.hours,
      commission: data.commission,
    };
  }

  async getTripHistory(driverId: string, limit: number, offset: number): Promise<TripHistoryDto[]> {
    // Mock trip history
    const mockTrips: TripHistoryDto[] = [
      {
        tripId: 'trip_001',
        date: '2024-01-15',
        time: '14:30',
        pickup: 'Downtown Chicago',
        dropoff: "O'Hare Airport",
        distance: 18.5,
        duration: 35,
        fare: 4500,
        netEarnings: 3600,
        rating: 5,
        riderName: 'Sarah Johnson',
      },
      {
        tripId: 'trip_002',
        date: '2024-01-15',
        time: '12:15',
        pickup: 'Lincoln Park',
        dropoff: 'Navy Pier',
        distance: 4.2,
        duration: 15,
        fare: 1800,
        netEarnings: 1440,
        rating: 5,
        riderName: 'Mike Chen',
      },
      {
        tripId: 'trip_003',
        date: '2024-01-15',
        time: '10:45',
        pickup: 'River North',
        dropoff: 'Millennium Park',
        distance: 2.8,
        duration: 12,
        fare: 1500,
        netEarnings: 1200,
        rating: 4,
        riderName: 'Emily Davis',
      },
    ];

    return mockTrips.slice(offset, offset + limit);
  }

  async getDashboard(driverId: string) {
    const driver = this.drivers.get(driverId);
    const currentOffer = this.currentOffers.get(driverId);
    const todayEarnings = await this.getEarnings(driverId, 'today');

    return {
      driver: {
        name: `${driver?.firstName} ${driver?.lastName}`,
        status: driver?.status || DriverStatus.OFFLINE,
        rating: driver?.rating || 0,
        totalTrips: driver?.totalTrips || 0,
      },
      todayStats: {
        earnings: todayEarnings.netEarnings,
        trips: todayEarnings.totalTrips,
        onlineHours: todayEarnings.onlineHours,
      },
      currentOffer,
      hasActiveTrip: driver?.status === DriverStatus.BUSY || 
                     driver?.status === DriverStatus.EN_ROUTE_PICKUP ||
                     driver?.status === DriverStatus.AT_PICKUP ||
                     driver?.status === DriverStatus.EN_ROUTE_DROPOFF,
    };
  }

  private simulateRideOffer(driverId: string) {
    // Simulate receiving a ride offer after going online
    setTimeout(() => {
      const mockOffer: RideOfferDto = {
        offerId: uuidv4(),
        tripId: uuidv4(),
        riderId: 'rider_123',
        riderName: 'Sarah Johnson',
        riderPhone: '+1-312-555-0456',
        pickup: {
          address: '123 N Michigan Ave, Chicago, IL',
          lat: 41.8781,
          lng: -87.6298,
        },
        dropoff: {
          address: "O'Hare International Airport, Terminal 1",
          lat: 41.9786,
          lng: -87.9048,
        },
        estimatedFare: 4500,
        netPayout: 3600,
        estimatedDistance: 18.5,
        estimatedDuration: 35,
        pickupEta: 8,
        category: 'black_sedan',
        specialInstructions: 'Flight departure at 3:30 PM - AA123',
        expiresAt: new Date(Date.now() + 5000).toISOString(), // 5 seconds
      };

      this.currentOffers.set(driverId, mockOffer);

      // Auto-expire the offer after 5 seconds
      setTimeout(() => {
        if (this.currentOffers.get(driverId)?.offerId === mockOffer.offerId) {
          this.currentOffers.delete(driverId);
        }
      }, 5000);
    }, 3000); // Send offer 3 seconds after going online
  }
}