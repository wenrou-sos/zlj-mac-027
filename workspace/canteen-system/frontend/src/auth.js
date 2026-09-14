const TOKEN_KEY = 'canteen_token'
const USER_KEY = 'canteen_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY))
  } catch {
    return null
  }
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/** 当前登录人是否具备任一指定角色 */
export function hasRole(...roles) {
  const u = getUser()
  return !!u && roles.includes(u.role)
}
