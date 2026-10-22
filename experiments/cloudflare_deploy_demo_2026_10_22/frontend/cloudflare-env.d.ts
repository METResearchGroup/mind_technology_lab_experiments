interface CloudflareEnv {
  API_BASE_URL: string;
  NOTE_TOKEN?: string;
}

declare module "cloudflare:workers" {
  export const env: CloudflareEnv;
}
