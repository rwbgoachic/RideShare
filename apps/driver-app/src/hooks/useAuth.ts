import { useState, useEffect, createContext, useContext } from 'react';
import apiService, { LoginRequest, DriverProfile } from '../services/api.service';

interface AuthContextType {
  isAuthenticated: boolean;
  driver: DriverProfile | null;
  login: (credentials: LoginRequest) => Promise<boolean>;
  register: (data: any) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
  error: string | null;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const useAuthState = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [driver, setDriver] = useState<DriverProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check if user is already authenticated
    const checkAuth = async () => {
      try {
        if (apiService.isAuthenticated()) {
          const profile = await apiService.getProfile();
          setDriver(profile);
          setIsAuthenticated(true);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        apiService.logout();
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (credentials: LoginRequest): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiService.login(credentials);
      
      if (response.success) {
        const profile = await apiService.getProfile();
        setDriver(profile);
        setIsAuthenticated(true);
        return true;
      } else {
        setError('Login failed');
        return false;
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Login failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const register = async (data: any): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiService.register(data);
      
      if (response.success) {
        return true;
      } else {
        setError('Registration failed');
        return false;
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Registration failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    apiService.logout();
    setDriver(null);
    setIsAuthenticated(false);
    setError(null);
  };

  const refreshProfile = async () => {
    try {
      if (apiService.isAuthenticated()) {
        const profile = await apiService.getProfile();
        setDriver(profile);
      }
    } catch (error) {
      console.error('Failed to refresh profile:', error);
    }
  };

  return {
    isAuthenticated,
    driver,
    login,
    register,
    logout,
    loading,
    error,
    refreshProfile,
  };
};

export { AuthContext };