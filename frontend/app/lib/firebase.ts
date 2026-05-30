import { initializeApp, getApps, FirebaseApp } from "firebase/app";
import { getAuth, signInAnonymously, connectAuthEmulator, Auth } from "firebase/auth";

// Lazy initialization — never runs during Next.js pre-rendering/build,
// only when first called from a browser useEffect or event handler.
let _app: FirebaseApp | null = null;
let _auth: Auth | null = null;
let _emulatorConnected = false;

function getFirebaseAuth(): Auth {
  if (!_auth) {
    if (!_app) {
      _app = getApps().length === 0
        ? initializeApp({
            apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
            authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
            projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
          })
        : getApps()[0];
    }
    _auth = getAuth(_app);
    if (
      !_emulatorConnected &&
      process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR === "true"
    ) {
      connectAuthEmulator(_auth, "http://localhost:9099", { disableWarnings: true });
      _emulatorConnected = true;
    }
  }
  return _auth;
}

export async function signInAnon(): Promise<string> {
  const cred = await signInAnonymously(getFirebaseAuth());
  return cred.user.uid;
}

export async function getIdToken(): Promise<string> {
  const auth = getFirebaseAuth();
  await auth.authStateReady(); // wait for auth state to restore from localStorage
  const user = auth.currentUser;
  if (!user) return "";
  return user.getIdToken();
}
