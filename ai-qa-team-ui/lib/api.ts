// src/lib/api.ts
"use client";

import axios from "axios";

const API = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// ---------------------------------------------------
//  ATTACH ACCESS TOKEN TO ALL REQUESTS
// ---------------------------------------------------
API.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ---------------------------------------------------
//  REFRESH TOKEN ON 401
// ---------------------------------------------------
let isRefreshing = false;
let failedRequestsQueue: any[] = [];

API.interceptors.response.use(
  (response) => response,

  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retrying → refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedRequestsQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers["Authorization"] = `Bearer ${token}`;
            return API(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      isRefreshing = true;

      try {
        const refresh_token = localStorage.getItem("refresh_token");
        if (!refresh_token) {
          throw new Error("No refresh token");
        }

        const res = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
          { refresh_token }
        );

        const newToken = res.data.access_token;

        // Store new token
        localStorage.setItem("access_token", newToken);

        // Retry failed original requests
        failedRequestsQueue.forEach((p) => p.resolve(newToken));
        failedRequestsQueue = [];

        originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
        isRefreshing = false;

        return API(originalRequest);
      } catch (err) {
        failedRequestsQueue.forEach((p) => p.reject(err));
        failedRequestsQueue = [];
        isRefreshing = false;

        // Clear local tokens
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");

        // Redirect user to login modal
        window.openAuth?.();

        return Promise.reject(err);
      }
    }

    return Promise.reject(error);
  }
);

export default API;
