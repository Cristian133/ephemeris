import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { DateProvider } from './context/DateContext'
import { LocationProvider } from './context/LocationContext'
import { ThemeProvider } from './context/ThemeContext'
import './styles/theme.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <LocationProvider>
          <DateProvider>
            <App />
          </DateProvider>
        </LocationProvider>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
)
