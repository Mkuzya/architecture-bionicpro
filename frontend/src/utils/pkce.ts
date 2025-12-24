/**
 * PKCE (Proof Key for Code Exchange) utilities
 * Generates code_verifier and code_challenge for OAuth 2.0 PKCE flow
 */

/**
 * Generates a cryptographically random string for code_verifier
 * @param length Length of the verifier (43-128 characters, recommended 43)
 * @returns Base64URL-encoded random string
 */
export function generateCodeVerifier(length: number = 43): string {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  
  // Convert to base64url
  const charArray = Array.from(array);
  return btoa(String.fromCharCode(...charArray))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
    .substring(0, length);
}

/**
 * Generates code_challenge from code_verifier using SHA256
 * @param verifier The code_verifier string
 * @returns Promise resolving to base64URL-encoded SHA256 hash
 */
export async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  
  // Convert to base64url
  const digestArray = new Uint8Array(digest);
  const charArray = Array.from(digestArray);
  return btoa(String.fromCharCode(...charArray))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

/**
 * Generates both code_verifier and code_challenge
 * @returns Promise resolving to object with verifier and challenge
 */
export async function generatePKCEPair(): Promise<{ verifier: string; challenge: string }> {
  const verifier = generateCodeVerifier();
  const challenge = await generateCodeChallenge(verifier);
  return { verifier, challenge };
}

