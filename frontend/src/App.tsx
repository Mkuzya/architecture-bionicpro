import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, { KeycloakConfig, KeycloakInitOptions } from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM||"",
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID||""
};

// Initialize Keycloak with PKCE support
const keycloak = new Keycloak(keycloakConfig);

// Configure Keycloak init options for PKCE
const initOptions: KeycloakInitOptions = {
  pkceMethod: 'S256', // Use SHA256 for PKCE
  checkLoginIframe: false, // Disable iframe check for better security
  enableLogging: process.env.NODE_ENV === 'development',
  // Don't store refresh token in browser (security requirement)
  // Keycloak will handle token refresh server-side if needed
};

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider 
      authClient={keycloak}
      initOptions={initOptions}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;