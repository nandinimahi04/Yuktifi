"use client";
import React, { useMemo } from "react";
import { MapContainer, TileLayer, Circle, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix leaflet icon issue in Next.js
const createIcon = (color: string) => {
  return new L.Icon({
    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${color}.png`,
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });
};

interface Competitor {
  name: string;
  distance_km?: number;
  lat?: number;
  lon?: number;
  latitude?: number;
  longitude?: number;
  category?: string;
  sources?: string[];
  address?: string;
}

interface MapComponentProps {
  lat: number;
  lng: number;
  radiusKm: number;
  showCompetitors?: boolean;
  showZones?: boolean;
  competitors?: Competitor[];
}

export default function MapComponent({ 
  lat = 17.6599, 
  lng = 75.9064, 
  radiusKm = 5, 
  showCompetitors = true, 
  showZones = true, 
  competitors = [] 
}: MapComponentProps) {
  const redIcon = useMemo(() => createIcon('red'), []);

  // Render only real mapped competitors
  const displayCompetitors = useMemo(() => {
    return (competitors || []).filter(c => Boolean(c && (c.name || c.category)));
  }, [competitors]);

  return (
    <MapContainer 
      center={[lat, lng]} 
      zoom={12} 
      style={{ height: "100%", width: "100%", minHeight: "480px", backgroundColor: '#f8f8f8' }} 
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
      />
      
      {/* Catchment Radius (Blue dashed border) */}
      <Circle 
        center={[lat, lng]} 
        radius={radiusKm * 1000} 
        pathOptions={{ color: '#2563eb', fillColor: '#3b82f6', fillOpacity: 0.05, weight: 2, dashArray: '6, 6' }} 
      />
      
      {/* High Opportunity Zones (Green circular zones) */}
      {showZones && (
        <>
          <Circle 
            center={[lat + 0.018, lng + 0.014]} 
            radius={(radiusKm * 1000) * 0.38} 
            pathOptions={{ color: '#16a34a', fillColor: '#22c55e', fillOpacity: 0.22, weight: 1.5 }} 
          />
          <Circle 
            center={[lat - 0.022, lng - 0.018]} 
            radius={(radiusKm * 1000) * 0.32} 
            pathOptions={{ color: '#16a34a', fillColor: '#22c55e', fillOpacity: 0.20, weight: 1.5 }} 
          />
        </>
      )}
      
      {/* Competitor Pins */}
      {showCompetitors && displayCompetitors.map((comp: any, idx) => {
        let compLat = comp.latitude ?? comp.lat;
        let compLng = comp.longitude ?? comp.lon;
        
        if (compLat === undefined || compLng === undefined || compLat === null || compLng === null) {
          const angle = (idx * (360 / Math.max(1, displayCompetitors.length))) * (Math.PI / 180);
          compLat = lat + ((comp.distance_km || 1) / 111) * Math.cos(angle);
          compLng = lng + ((comp.distance_km || 1) / (111 * Math.cos(lat * (Math.PI / 180)))) * Math.sin(angle);
        }
        
        return (
          <Marker key={idx} position={[compLat, compLng]} icon={redIcon}>
            <Popup>
              <div className="font-sans text-xs">
                <strong className="block text-sm font-bold text-ink mb-0.5">{comp.name.replace(/_/g, ' ')}</strong>
                <span className="text-ink-soft">{comp.distance_km ? `${comp.distance_km.toFixed(1)} km away` : 'Direct Competitor'}</span>
              </div>
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
