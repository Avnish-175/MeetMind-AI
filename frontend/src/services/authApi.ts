import axios from 'axios';
import api from './api';
import type {
  AuthUser,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
} from '../types/auth';

export async function registerUser(payload: RegisterRequest): Promise<AuthUser> {
  const response = await api.post<AuthUser>('/api/v1/auth/register', payload);
  return response.data;
}

export async function loginUser(payload: LoginRequest): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>('/api/v1/auth/login', payload);
  return response.data;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const response = await api.get<AuthUser>('/api/v1/auth/me');
  return response.data;
}

export function extractAuthErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return 'Unable to connect to the server. Please check your connection and try again.';
    }

    const status = error.response.status;
    if (status === 401) {
      return 'Invalid email or password.';
    }
    if (status === 409) {
      return 'An account with this email already exists.';
    }
    if (status === 422) {
      return 'Please check your input and ensure all fields are valid.';
    }
    if (status >= 500) {
      return 'A server error occurred. Please try again later.';
    }
  }

  return 'An unexpected error occurred. Please try again.';
}
