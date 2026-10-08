/**
 * 坐标转换工具
 * WGS-84 (GPS) → GCJ-02 (国测局) → BD-09 (百度)
 *
 * 百度地图使用 BD-09 坐标系
 * 后端存储的是 WGS-84 标准GPS坐标
 * 使用时需要先转换为 BD-09 才能在百度地图上正确显示
 */

const PI = Math.PI
const X_PI = (PI * 3000.0) / 180.0
const A = 6378245.0 // 长半轴
const EE = 0.00669342162296594323 // 扁率

/**
 * 判断坐标是否在中国境外
 */
function outOfChina(lng, lat) {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
}

function transformLat(x, y) {
  let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  ret += ((20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0) / 3.0
  ret += ((20.0 * Math.sin(y * PI) + 40.0 * Math.sin((y / 3.0) * PI)) * 2.0) / 3.0
  ret += ((160.0 * Math.sin((y / 12.0) * PI) + 320.0 * Math.sin((y * PI) / 30.0)) * 2.0) / 3.0
  return ret
}

function transformLng(x, y) {
  let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  ret += ((20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0) / 3.0
  ret += ((20.0 * Math.sin(x * PI) + 40.0 * Math.sin((x / 3.0) * PI)) * 2.0) / 3.0
  ret += ((150.0 * Math.sin((x / 12.0) * PI) + 300.0 * Math.sin((x / 30.0) * PI)) * 2.0) / 3.0
  return ret
}

/**
 * WGS-84 → GCJ-02 转换
 * @param {number} lng - 经度
 * @param {number} lat - 纬度
 * @returns {{lng: number, lat: number}}
 */
export function wgs84ToGcj02(lng, lat) {
  if (outOfChina(lng, lat)) {
    return { lng, lat }
  }
  let dLat = transformLat(lng - 105.0, lat - 35.0)
  let dLng = transformLng(lng - 105.0, lat - 35.0)
  const radLat = (lat / 180.0) * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / (((A * (1 - EE)) / (magic * sqrtMagic)) * PI)
  dLng = (dLng * 180.0) / ((A / sqrtMagic) * Math.cos(radLat) * PI)
  return {
    lng: lng + dLng,
    lat: lat + dLat
  }
}

/**
 * GCJ-02 → BD-09 转换
 * @param {number} lng - 经度
 * @param {number} lat - 纬度
 * @returns {{lng: number, lat: number}}
 */
export function gcj02ToBd09(lng, lat) {
  const z = Math.sqrt(lng * lng + lat * lat) + 0.00002 * Math.sin(lat * X_PI)
  const theta = Math.atan2(lat, lng) + 0.000003 * Math.cos(lng * X_PI)
  return {
    lng: z * Math.cos(theta) + 0.0065,
    lat: z * Math.sin(theta) + 0.006
  }
}

/**
 * WGS-84 → BD-09 一键转换（推荐使用）
 * @param {number} lng - WGS-84 经度
 * @param {number} lat - WGS-84 纬度
 * @returns {{lng: number, lat: number}} BD-09 坐标
 */
export function wgs84ToBd09(lng, lat) {
  const gcj02 = wgs84ToGcj02(lng, lat)
  return gcj02ToBd09(gcj02.lng, gcj02.lat)
}

/**
 * GPS坐标映射到2D地图坐标
 * @param {number} lng - 经度
 * @param {number} lat - 纬度
 * @param {{minLng: number, maxLng: number, minLat: number, maxLat: number}} bounds - GPS边界
 * @param {{width: number, height: number}} mapSize - 2D地图尺寸
 * @returns {{mapX: number, mapY: number}}
 */
export function gpsToMap2D(lng, lat, bounds, mapSize) {
  const xRatio = (lng - bounds.minLng) / (bounds.maxLng - bounds.minLng)
  const yRatio = (bounds.maxLat - lat) / (bounds.maxLat - bounds.minLat) // 注意Y轴翻转
  return {
    mapX: Math.round(xRatio * mapSize.width),
    mapY: Math.round(yRatio * mapSize.height)
  }
}
