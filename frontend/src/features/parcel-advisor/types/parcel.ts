export type ParcelStatus = 'healthy' | 'warning' | 'critical';

export interface Parcel {
  id: string;
  name: string;
  country: string;
  region: string;
  crop: string;
  areaHa: number;
  lat: number;
  lng: number;
  ndvi: number;
  soilMoisture: number;
  temperature: number;
  humidity: number;
  status: ParcelStatus;
  recommendation: string;
}
