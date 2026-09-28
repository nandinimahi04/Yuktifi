"use client";
import React from "react";
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
  distance_km: number;
  lat?: number;
  lon?: number;
}

interface MapComponentProps {
  lat: number;
  lng: number;
  radiusKm: number;
  showCompetitors: boolean;
  showZones: boolean;
  competitors: Competitor[];
}

export default function MapComponent({ lat, lng, radiusKm, showCompetitors, showZones, competitors }: MapComponentProps) {
  const redIcon = createIcon('red');
  const blueIcon = createIcon('blue');

  return (
    <MapContainer center={[lat, lng]} zoom={12} style={{ height: "100%", width: "100%", backgroundColor: '#f8f8f8' }} scrollWheelZoom={false}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url={`https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${process.env.NEXT_PUBLIC_CARTO_ACCESS_TOKEN}`}
      />
      
      {/* Core Catchment Radius */}
      <Circle 
        center={[lat, lng]} 
        radius={radiusKm * 1000} 
        pathOptions={{ color: '#2563eb', fillColor: '#3b82f6', fillOpacity: 0.08, weight: 2, dashArray: '4, 4' }} 
      />
      
      {/* Opp Zone (Green Heatmap/Polygon proxy) */}
      {showZones && (
        <>
          <Circle 
            center={[lat + 0.015, lng + 0.01]} 
            radius={(radiusKm * 1000) * 0.4} 
            pathOptions={{ color: '#16a34a', fillColor: '#22c55e', fillOpacity: 0.18, weight: 1.5 }} 
          />
          <Circle 
            center={[lat - 0.02, lng - 0.015]} 
            radius={(radiusKm * 1000) * 0.3} 
            pathOptions={{ color: '#16a34a', fillColor: '#22c55e', fillOpacity: 0.15, weight: 1.5 }} 
          />
        </>
      )}

      <Marker position={[lat, lng]} icon={blueIcon}>
        <Popup>Target Location</Popup>
      </Marker>
      
      {showCompetitors && competitors.map((comp, idx) => {
        let compLat = lat;
        let compLng = lng;
        
        if (comp.lat && comp.lon) {
          compLat = comp.lat;
          compLng = comp.lon;
        } else {
          // Generate deterministic fake coordinates if real ones are missing
          const angle = (idx * (360 / Math.max(1, competitors.length))) * (Math.PI / 180);
          compLat = lat + (comp.distance_km / 111) * Math.cos(angle);
          compLng = lng + (comp.distance_km / (111 * Math.cos(lat * (Math.PI / 180)))) * Math.sin(angle);
        }
        
        return (
          <Marker key={idx} position={[compLat, compLng]} icon={redIcon}>
            <Popup>{comp.name}<br/>{comp.distance_km.toFixed(1)} km away</Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
