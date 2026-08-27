export const RELEASE_TAG = 'v1.0.5';
export const RELEASE_PAGE_URL = 'https://github.com/Izayauh/Impulse/releases/latest';
export const DOWNLOAD_URL = import.meta.env.VITE_PUBLIC_DOWNLOAD_URL || RELEASE_PAGE_URL;
export const CHANGELOG_URL = 'https://github.com/Izayauh/Impulse/blob/main/CHANGELOG.md';
export const PRIVACY_URL = 'https://github.com/Izayauh/Impulse/blob/main/PRIVACY.md';
export const LICENSE_URL = 'https://github.com/Izayauh/Impulse/blob/main/LICENSE';
export const GITHUB_REPO_URL = 'https://github.com/Izayauh/Impulse';
export const CONTACT_EMAIL = 'beta@impulsedictation.com';

// One-time price, shown everywhere the buy path appears.
export const PRICE = '$29';
// Lemon Squeezy checkout. Overridable per-deploy so the exact product URL can
// be swapped in without a rebuild once the store is activated.
export const BUY_URL = import.meta.env.VITE_PUBLIC_BUY_URL || 'https://impulsevoice.lemonsqueezy.com/';
