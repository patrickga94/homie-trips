import axios from 'axios'

// Single axios instance for the whole app.
// - baseURL '/api' matches the Django routes (and the Vite dev proxy).
// - withCredentials sends the Django session cookie.
// - xsrf* options make axios read the csrftoken cookie and echo it back in the
//   X-CSRFToken header that Django's CSRF protection expects.
const client = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

export default client
