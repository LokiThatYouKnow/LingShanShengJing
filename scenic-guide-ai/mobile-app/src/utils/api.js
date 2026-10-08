// API基础配置
const BASE_URL = 'http://localhost:8000'

// 通用请求封装
export const request = (options) => {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...options.header
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res.data)
        }
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

// 上传文件
export const uploadFile = (options) => {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + options.url,
      filePath: options.filePath,
      name: options.name || 'file',
      formData: options.formData || {},
      success: (res) => {
        const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data
        resolve(data)
      },
      fail: reject
    })
  })
}

// 景区API
export const scenicApi = {
  getInfo: () => request({ url: '/api/scenic/info' }),
  getSpots: () => request({ url: '/api/scenic/spots' }),
  getSpotDetail: (id) => request({ url: `/api/scenic/spots/${id}` }),
  getNearby: (lat, lng, radius = 200) => request({
    url: `/api/scenic/nearby?lat=${lat}&lng=${lng}&radius=${radius}`
  }),
  getRouteTemplates: () => request({ url: '/api/scenic/route/templates' }),
  recommendRoute: (preferences) => request({
    url: '/api/scenic/route/recommend',
    method: 'POST',
    data: { preferences }
  })
}

// 聊天API
export const chatApi = {
  sendMessage: (data) => request({
    url: '/api/chat/message',
    method: 'POST',
    data
  }),
  sendVoice: (filePath, sessionId, deviceId, spotId) => {
    return uploadFile({
      url: '/api/chat/voice',
      filePath,
      name: 'audio',
      formData: {
        session_id: sessionId || '',
        device_id: deviceId || '',
        platform: 'app',
        spot_id: spotId || '',
        generate_audio: 'true'
      }
    })
  },
  getHistory: (sessionId) => request({ url: `/api/chat/history/${sessionId}` }),
  getSessions: (deviceId) => request({ url: `/api/chat/sessions/${deviceId}` }),
  rateSession: (sessionId, score) => request({
    url: `/api/chat/session/${sessionId}/rate?score=${score}`,
    method: 'POST'
  })
}

export default { BASE_URL, request, uploadFile, scenicApi, chatApi }
