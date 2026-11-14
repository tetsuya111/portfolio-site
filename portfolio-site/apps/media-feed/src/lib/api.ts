"use client"

import axios from "axios";

//export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export const getMediaUrl = (content: Content) => {
  // media_url があればそれを使う（CDN等の直接配信URL）。無ければ従来のアプリ経由。
  if (content.media_url) return content.media_url;
  return content.path ? `${BASE_URL}/contents/${content.id}/media/` : content.link;
}

export const getPosterUrl = (content: Content): string | undefined =>
  content.poster_url || undefined;

// ポートフォリオのモックは fetch だけを横取りするため、axios の通信を fetch で行う
// （api インスタンスのほか、ログイン・トークン更新で使う axios.post も対象にする）
axios.defaults.adapter = "fetch";

export const api = axios.create({ baseURL: BASE_URL, adapter: "fetch" });

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401) {
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE_URL.replace("/api", "")}/api/auth/token/refresh/`, { refresh });
          localStorage.setItem("access_token", data.access);
          err.config.headers.Authorization = `Bearer ${data.access}`;
          return api(err.config);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
      }
    }
    return Promise.reject(err);
  }
);

export type ContentType = "image" | "video";

export interface Tag { name: string; content_count?: number }
export interface ContentDetail { series_id: string; series_number: number }
export interface Content {
  id: string; type: ContentType; title: string; path: string;
  link: string; source_url: string; user: string; description: string;
  tags: Tag[]; detail?: ContentDetail; created_at: string;
  media_url?: string; poster_url?: string;
}
export interface Profile { username: string; description: string }
export interface FollowingUser { username: string }
export interface BookmarkedContent {
  id: string; content: Content; is_published: boolean;
}
export interface Comment {
  id: number; username: string; text: string;
  created_at: string; updated_at: string;
}

export const contentsApi = {
  
  list: (params?: Record<string, string | string[]>) =>
    api.get<{ results: Content[]; count: number }>("/contents/", { params }),
  get: (id: string) => api.get<Content>(`/contents/${id}/`),
  getBySeries: (series_id: string, series_number: number) =>
    api.get<{ results: Content[]; count: number }>("/contents/", {
      params: { series_id, series_number: String(series_number) },
    }),
  getBySeriesRandom: (series_id: string) =>
    api.get<{ results: Content[]; count: number }>("/contents/", {
      params: { series_id, random: "true" },
    }),
  related: (id: string) =>
    api.get<{ results: Content[]; count: number }>(`/contents/${id}/related/`),
};

export const tagsApi = {
  list: () => api.get<Tag[]>("/tags/"),
};

export interface UserProfile { username: string; description: string }

export const usersApi = {
  list: (q?: string) =>
    api.get<UserProfile[]>("/users/", { params: q ? { q } : undefined }),
};

export const profileApi = {
  get: (username: string) => api.get<Profile>(`/profile/${username}/`),
  update: (username: string, data: Partial<Profile>) =>
    api.put<Profile>(`/profile/${username}/`, data),
};

export const bookmarkApi = {
  list: (username: string) =>
    api.get<BookmarkedContent[]>(`/bookmarks/${username}/`),
  add: (username: string, content_id: string) =>
    api.post(`/bookmarks/${username}/`, { content_id }),
  remove: (username: string, bookmark_id: string) =>
    api.delete(`/bookmarks/${username}/${bookmark_id}/`),
  download: (username: string, content_ids: string[]) =>
    api.post(`/bookmarks/${username}/download/`, { content_ids }, { responseType: 'blob' }),
};

export const followingApi = {
  list: (username: string) =>
    api.get<{ following_users: FollowingUser[] }>(`/following/${username}/`),
  follow: (username: string, target: string) =>
    api.post(`/following/${username}/`, { target }),
  unfollow: (username: string, target: string) =>
    api.delete(`/following/${username}/${target}/`),
};

export const commentsApi = {
  list: (content_id: string) =>
    api.get<Comment[]>(`/comments/${content_id}/`),
  add: (content_id: string, text: string) =>
    api.post(`/comments/${content_id}/`, { text }),
  update: (comment_id: number, text: string) =>
    api.put(`/comments/detail/${comment_id}/`, { text }),
  remove: (comment_id: number) =>
    api.delete(`/comments/detail/${comment_id}/`),
};

export interface UserMe {
  username: string;
  is_affiliate: boolean;
  is_uploader: boolean;
  is_author: boolean;
}

export const authApi = {
  register: (username: string, password: string) =>
    api.post("/auth/register/", { username, password }),
  login: (username: string, password: string) =>
    axios.post(`${BASE_URL.replace("/api", "")}/api/auth/login/`, { username, password }),
  deleteAccount: () => api.delete("/auth/user/"),
  me: () => api.get<UserMe>("/auth/me/"),
};

export interface ArticleTag { name: string; article_count?: number }
export interface Article {
  id: number;
  title: string;
  description: string;
  username: string;
  contents: Content[];
  thumbnail: Content | null;
  article_tags: ArticleTag[];
  created_at: string;
  updated_at: string;
}

export const articlesApi = {
  list: (params?: Record<string, string>) =>
    api.get<{ results: Article[]; count: number }>("/articles/", { params }),
  get: (id: number, params?: Record<string, string>) =>
    api.get<Article>(`/articles/${id}/`, { params }),
  create: (data: {
    title: string;
    description: string;
    content_ids: string[];
    thumbnail_id?: string | null;
    article_tag_names?: string[];
  }) => api.post<Article>("/articles/", data),
  remove: (id: number) => api.delete(`/articles/${id}/`),
};

export const articleTagsApi = {
  list: () => api.get<ArticleTag[]>("/article-tags/"),
};

export interface ClickCountItem {
  id: number;
  created_at: string;
  referrer: string;
  page_link: string;
  ip_address: string | null;
}

export const clickCountApi = {
  get: (period?: string) =>
    api.get<{ count: number; results: ClickCountItem[] }>("/click-counts/", {
      params: period ? { period } : undefined,
    }),
};

export const inquiryApi = {
  send: (data: { name: string; title: string; email: string; content: string }) =>
    api.post<{ id: number }>("/inquiries/", data),
};

export interface AdContent {
  id: number;
  html: string;
  width: number | null;
  height: number | null;
  tags: string[];
}

export const adContentApi = {
  list: (params?: { tag?: string | string[]; number?: number; random?: boolean }) =>
    api.get<AdContent[]>("/ad-contents/", {
      params: params
        ? {
            ...(params.tag ? (Array.isArray(params.tag) ? { tag: params.tag } : { tag: params.tag }) : {}),
            ...(params.number !== undefined ? { number: params.number } : {}),
            ...(params.random ? { random: "true" } : {}),
          }
        : undefined,
    }),
};
