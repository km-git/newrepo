import type { AreaPage } from "./types";

export interface PublishResult {
  success: boolean;
  postId?: number;
  url?: string;
  message: string;
}

export function publishToWordPress(page: AreaPage): PublishResult {
  if (process.env.WORDPRESS_URL && process.env.WORDPRESS_APP_PASSWORD) {
    return {
      success: false,
      message: "Live WordPress publish not configured in MVP — use mock mode",
    };
  }

  const postId = Math.floor(1000 + Math.random() * 9000);
  const base = process.env.WORDPRESS_MOCK_URL ?? "https://example.com";
  console.log(`[MOCK WordPress] Published: ${page.slug} as post ${postId}`);

  return {
    success: true,
    postId,
    url: `${base}/${page.slug}/`,
    message: `Published to WordPress as draft post #${postId}`,
  };
}
