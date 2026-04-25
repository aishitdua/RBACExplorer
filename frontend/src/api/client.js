import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

let _authToken = null

export function setAuthToken(token) {
  _authToken = token
}

client.interceptors.request.use((config) => {
  if (_authToken) {
    config.headers.Authorization = `Bearer ${_authToken}`
  }
  return config
})

export default client
