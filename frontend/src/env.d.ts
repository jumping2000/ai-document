interface ImportMetaEnv {
  // Vite env variables go here. Keep generic to avoid build-time failures.
  readonly [key: string]: any;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
