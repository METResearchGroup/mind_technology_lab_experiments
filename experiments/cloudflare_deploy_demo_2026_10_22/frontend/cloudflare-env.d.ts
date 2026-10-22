interface ApiFetcher {
  fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response>;
}

interface CloudflareEnv {
  API_BASE_URL: string;
  NOTE_TOKEN?: string;
  API: ApiFetcher;
}

declare module "cloudflare:workers" {
  export const env: CloudflareEnv;
}
