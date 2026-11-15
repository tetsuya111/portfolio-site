"use client";

export function getUsername(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("username");
}

export function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("username");
  localStorage.removeItem("is_affiliate");
  localStorage.removeItem("is_uploader");
  localStorage.removeItem("is_author");
}

export interface UserPermissions {
  is_affiliate: boolean;
  is_uploader: boolean;
  is_author: boolean;
}

export function getUserPermissions(): UserPermissions {
  if (typeof window === "undefined") {
    return { is_affiliate: false, is_uploader: false, is_author: false };
  }
  return {
    is_affiliate: localStorage.getItem("is_affiliate") === "true",
    is_uploader: localStorage.getItem("is_uploader") === "true",
    is_author: localStorage.getItem("is_author") === "true",
  };
}

export function setUserPermissions(perms: UserPermissions): void {
  localStorage.setItem("is_affiliate", String(perms.is_affiliate));
  localStorage.setItem("is_uploader", String(perms.is_uploader));
  localStorage.setItem("is_author", String(perms.is_author));
}

export function isTurnstileVerified(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c === "turnstile_verified=true");
}

export function setTurnstileVerified(): void {
  const expires = new Date();
  expires.setMinutes(expires.getMinutes() + 10);
  document.cookie = `turnstile_verified=true; expires=${expires.toUTCString()}; path=/`;
}
