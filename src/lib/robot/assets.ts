// Where the robot's model, paint textures and the candidates' portraits live
// (CloudFront over the assets bucket, not the deploy). PUBLIC_ASSET_BASE
// overrides it.
import { env } from '$env/dynamic/public';

export const DEFAULT_ASSET_BASE = 'https://assets.simulacraamericana.com/';

/** The base URL with exactly one trailing slash; the default when unset or blank. */
export function normalizeAssetBase(raw: string | undefined): string {
  const value = raw?.trim() ?? '';
  if (value === '') return DEFAULT_ASSET_BASE;
  return value.endsWith('/') ? value : `${value}/`;
}

export const ASSET_BASE = normalizeAssetBase(env.PUBLIC_ASSET_BASE);

export function assetUrl(path: string): string {
  return `${ASSET_BASE}${path.replace(/^\/+/, '')}`;
}
