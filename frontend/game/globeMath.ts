import * as THREE from 'three';

/** 经纬度 → 球面三维坐标（Y 轴为北极） */
export function latLngToSphere(lat: number, lng: number, radius: number): THREE.Vector3 {
  const phi = THREE.MathUtils.degToRad(90 - lat);
  const theta = THREE.MathUtils.degToRad(lng + 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

/** 球面坐标 → 经纬度 */
export function sphereToLatLng(pos: THREE.Vector3): { lat: number; lng: number } {
  const normalized = pos.clone().normalize();
  const lat = 90 - THREE.MathUtils.radToDeg(Math.acos(normalized.y));
  const lng = THREE.MathUtils.radToDeg(Math.atan2(normalized.z, -normalized.x)) - 180;
  return { lat, lng };
}
