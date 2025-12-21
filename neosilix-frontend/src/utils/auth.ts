import axios, { AxiosResponse } from "axios";

const API_URL = "http://localhost:5000";

export async function login(email: string, password: string) {
  console.log("Logging in", email); // debug
  const res = await axios.post("http://localhost:5000/auth/login", { email, password });
  console.log(res.data); // debug
  if (!res.data || !res.data.token || !res.data.user) {
    throw new Error("Invalid server response");
  }
  return res.data;
}

export interface User {
  id: number;
  email: string;
  role: string;
  plan: string;
  trial_ends: string;
  is_admin: boolean;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export function getToken(): string | null {
  return localStorage.getItem("token");
}

export function getUser(): User | null {
  const user = localStorage.getItem("user");
  return user ? (JSON.parse(user) as User) : null;
}

export function authHeader() {
  const token = getToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function fetchWithAuth<T = any>(
  url: string
): Promise<AxiosResponse<T>> {
  return axios.get<T>(API_URL + url, { headers: authHeader() });
}
