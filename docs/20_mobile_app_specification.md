# SECTION 14 — MOBILE APP SPECIFICATION

## 14.1 PWA Screen Inventory (Phase 1 — Next.js)

| Screen | Route | Key Components | Actions | Offline? |
|---|---|---|---|---|
| Login | /login | Email/password form, TOTP field, SSO button, biometric trigger (if prev. authed) | Login, SSO, biometric | ❌ |
| Home Dashboard | /dashboard | Attendance status card, leave balance chips, pending actions count, recent payslip preview, notification bell | Check-in/out, quick leave apply | ✅ (cached) |
| Check In/Out | /attendance/punch | GPS map pin (Leaflet.js), current time, geofence status indicator, face capture option | Confirm check-in, confirm checkout | ❌ (needs GPS + API) |
| Apply Leave | /leave/apply | Leave type tabs, date range picker, balance preview (live), conflict calendar, reason textarea | Submit, save draft | ✅ (queue offline) |
| My Leave Status | /leave/my | Request list with status timeline steps, cancel button on pending | View detail, cancel | ✅ (cached list) |
| My Payslips | /payslips | Month/year filter, payslip card list, net salary shown | View detail, download PDF | ✅ (last 3 cached) |
| Payslip Detail | /payslips/{run_id} | Earnings breakdown, deductions table, net salary, download button | Download PDF | ✅ (cached) |
| Notifications | /notifications | Grouped notification list (Today/Earlier), unread badge, swipe-to-dismiss | Read, tap to navigate | ✅ (cached) |
| Team Directory | /directory | Search bar, department filter, employee cards with photo | Search, tap to view profile | ✅ (cached) |
| My Profile | /profile | Profile photo, contact info, emergency contact, bank details (masked) | Edit contact info | ✅ (cached) |
| Change Password | /settings/password | Current password, new password, confirm, strength indicator | Submit | ❌ |
| Settings | /settings | Notification prefs toggles (per channel per event), biometric toggle, language, theme | Toggle, save | ✅ |
| Offline Queue | /offline-queue | List of pending sync items (check-ins, leave drafts), sync status | Force sync, delete | ✅ |

---

## 14.2 React Native Additional Screens (Phase 2 — Expo)

| Screen | Native Feature | Key Components | Actions |
|---|---|---|---|
| Biometric Login | FaceID / TouchID (expo-local-authentication) | Biometric prompt, fallback to PIN | Authenticate, disable biometric |
| Face Capture (Attendance) | Camera (expo-camera) | Camera view, face detection overlay, alignment guide, capture feedback | Capture, retake, submit |
| Push Notification Permission | FCM/APNs (expo-notifications) | Permission request modal, benefit description | Allow, deny |
| Biometric Setup | expo-local-authentication | Enrollment flow, test scan, backup PIN setup | Enroll, cancel |
| Offline Payslip Viewer | Expo FileSystem | Cached PDF list, last sync time | View cached, refresh |
| GPS Background Track (field workers) | expo-location (background) | Background location service toggle, battery impact warning | Enable/disable |
| Deep Link Handler | expo-linking | Handles hrms://leave/approve/{id} links from notification tap | Navigate to correct screen |

---

## 14.3 Offline-First Strategy

### What Gets Cached (Service Worker + AsyncStorage)

```typescript
// frontend/lib/offline/cache-strategy.ts

export const CACHE_MANIFEST = {
  // ── Immediate cache on login ───────────────────────────────────
  on_login: [
    { key: "employee_profile",      ttl: 86400,  endpoint: "/api/v1/employees/me" },
    { key: "leave_balances",        ttl: 3600,   endpoint: "/api/v1/leave/balance/me" },
    { key: "leave_types",           ttl: 604800, endpoint: "/api/v1/leave/types" },
    { key: "public_holidays",       ttl: 604800, endpoint: "/api/v1/leave/public-holidays" },
    { key: "last_3_payslips",       ttl: 86400,  endpoint: "/api/v1/payroll/me/payslips?per_page=3" },
    { key: "notifications",         ttl: 300,    endpoint: "/api/v1/notifications?unread=true" },
    { key: "team_directory",        ttl: 3600,   endpoint: "/api/v1/employees?per_page=100" },
    { key: "company_announcements", ttl: 1800,   endpoint: "/api/v1/announcements?per_page=20" },
    { key: "notification_prefs",    ttl: 86400,  endpoint: "/api/v1/notifications/preferences" },
  ],

  // ── Cached on view ─────────────────────────────────────────────
  on_view: [
    { key: "payslip_{run_id}",      ttl: 2592000 }, // 30 days — payslips don't change
    { key: "attendance_this_month", ttl: 1800,   endpoint: "/api/v1/attendance?month=current" },
    { key: "leave_requests",        ttl: 600,    endpoint: "/api/v1/leave/requests?my=true" },
  ],

  // ── Offline write queue (synced on reconnect) ──────────────────
  offline_write_queue: [
    "attendance_checkin",   // GPS coords + timestamp stored locally
    "attendance_checkout",  // synced in order
    "leave_request_draft",  // saved locally, submitted when online
  ],
};


// Service Worker: next.config.js with next-pwa
// frontend/next.config.js
const withPWA = require("next-pwa")({
  dest: "public",
  disable: process.env.NODE_ENV === "development",
  runtimeCaching: [
    {
      urlPattern: /^https:\/\/api\.hrms\.company\.com\/api\/v1\/employees\/me/,
      handler: "StaleWhileRevalidate",
      options: {
        cacheName: "employee-profile",
        expiration: { maxAgeSeconds: 86400 },
      },
    },
    {
      urlPattern: /^https:\/\/api\.hrms\.company\.com\/api\/v1\/leave\/balance/,
      handler: "NetworkFirst",    // always try network, fall back to cache
      options: {
        cacheName: "leave-balance",
        networkTimeoutSeconds: 3,
        expiration: { maxAgeSeconds: 3600 },
      },
    },
    {
      urlPattern: /^https:\/\/api\.hrms\.company\.com\/api\/v1\/payroll\/.*\/payslips/,
      handler: "CacheFirst",     // payslips rarely change once generated
      options: {
        cacheName: "payslips",
        expiration: {
          maxEntries: 12,          // last 12 months
          maxAgeSeconds: 2592000,  // 30 days
        },
      },
    },
  ],
});
```

### Offline Sync Protocol

```typescript
// frontend/lib/offline/sync-manager.ts
import { openDB, DBSchema } from "idb";

interface OfflineAction {
  id: string;
  type: "checkin" | "checkout" | "leave_request";
  payload: Record<string, unknown>;
  timestamp: number;
  retries: number;
  status: "pending" | "syncing" | "synced" | "error";
  error?: string;
}

const db = await openDB<{offlineQueue: OfflineAction}>("hrms-offline", 1, {
  upgrade(db) {
    db.createObjectStore("offlineQueue", { keyPath: "id" });
  },
});


export class SyncManager {
  private isSyncing = false;

  /**
   * Queue an action for offline sync.
   * Called when user performs action while offline or network fails.
   */
  async queueAction(type: OfflineAction["type"], payload: Record<string, unknown>) {
    const action: OfflineAction = {
      id: crypto.randomUUID(),
      type,
      payload,
      timestamp: Date.now(),
      retries: 0,
      status: "pending",
    };
    await db.add("offlineQueue", action);

    // Show in-app toast: "Saved offline. Will sync when connected."
    showToast("Saved offline — will sync when you reconnect", "info");

    return action.id;
  }

  /**
   * Process offline queue — called when online event fires.
   */
  async syncAll() {
    if (this.isSyncing || !navigator.onLine) return;
    this.isSyncing = true;

    const pending = await db.getAll("offlineQueue");
    const sorted = pending
      .filter(a => a.status === "pending")
      .sort((a, b) => a.timestamp - b.timestamp); // FIFO order

    for (const action of sorted) {
      await db.put("offlineQueue", { ...action, status: "syncing" });

      try {
        await this.executeAction(action);
        await db.put("offlineQueue", { ...action, status: "synced" });
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        await db.put("offlineQueue", {
          ...action,
          status: action.retries >= 3 ? "error" : "pending",
          retries: action.retries + 1,
          error: errorMessage,
        });
      }
    }

    // Clean up synced items older than 7 days
    const allActions = await db.getAll("offlineQueue");
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
    for (const a of allActions) {
      if (a.status === "synced" && a.timestamp < cutoff) {
        await db.delete("offlineQueue", a.id);
      }
    }

    this.isSyncing = false;
    notifyUser(`${sorted.length} actions synced successfully`);
  }

  private async executeAction(action: OfflineAction) {
    const API = process.env.NEXT_PUBLIC_API_URL;

    const endpoints: Record<OfflineAction["type"], string> = {
      checkin: `${API}/api/v1/attendance/checkin`,
      checkout: `${API}/api/v1/attendance/checkout`,
      leave_request: `${API}/api/v1/leave/requests`,
    };

    const response = await fetch(endpoints[action.type], {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken()}`,
      },
      body: JSON.stringify(action.payload),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
  }
}

// Register online event listener
const syncManager = new SyncManager();
window.addEventListener("online", () => syncManager.syncAll());
```

### Conflict Resolution
```
CONFLICT SCENARIOS AND RESOLUTION:

1. Offline check-in, then online check-in attempted:
   Resolution: Server checks for existing check-in in same day
   If exists → return 409 with existing record (idempotent)
   Client: show "Already checked in at 09:12" — do not duplicate

2. Leave request submitted offline, then internet restored:
   Resolution: Submit with offline timestamp preserved
   Server: validates as of submission_timestamp, not sync_timestamp
   If leave already booked in same period (conflict):
   → Return 409 → User sees conflict → User cancels or modifies

3. Profile update cached offline, server has newer version:
   Resolution: "Last write wins" with timestamp comparison
   Server: updated_at check — if server newer, return 409 with server version
   Client: show "Server version is newer — merge manually?" with diff view
```

---

## 14.4 Push Notification Architecture (FCM + APNs)

```
PUSH NOTIFICATION FLOW:
─────────────────────────────────────────────────────────

1. DEVICE REGISTRATION (on first app load)
   ┌─────────────────────────────────────────────────────┐
   │ PWA:                                                │
   │   a) navigator.serviceWorker.register()             │
   │   b) reg.pushManager.subscribe({                    │
   │        applicationServerKey: VAPID_PUBLIC_KEY       │
   │      })                                             │
   │   c) POST /api/v1/devices {                         │
   │        token: subscription.endpoint,                │
   │        type: "web", platform: "pwa"                 │
   │      }                                              │
   │                                                     │
   │ React Native (Expo):                                │
   │   a) Notifications.requestPermissionsAsync()        │
   │   b) token = await Notifications.getExpoPushTokenAsync()│
   │      OR getDevicePushTokenAsync() for native FCM    │
   │   c) POST /api/v1/devices {                         │
   │        token: token,                                │
   │        type: "fcm|apns",                            │
   │        platform: "android|ios"                      │
   │      }                                              │
   └─────────────────────────────────────────────────────┘

2. TOKEN STORAGE
   Table: device_tokens
   Columns: id, tenant_id, employee_id, token, type (fcm/apns/web),
            platform (android/ios/pwa), is_active, last_used_at

3. BACKEND TRIGGER (Celery notification task)
   ┌─────────────────────────────────────────────────────┐
   │ Celery task: send_push_notification.delay(          │
   │   recipient_id="emp_uuid",                          │
   │   title="Leave Approved",                           │
   │   body="Your 3-day Annual Leave is confirmed",      │
   │   data={"screen": "/leave/my", "request_id": "uuid"}│
   │ )                                                   │
   └─────────────────────────────────────────────────────┘

4. NOTIFICATION DISPATCH
```

```python
# services/push_notification_service.py
from firebase_admin import messaging, credentials, initialize_app
from aioapns import APNs, NotificationRequest
import asyncio
import os

# Firebase Admin SDK (for FCM + web push)
cred = credentials.Certificate(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
firebase_app = initialize_app(cred)

async def send_push_to_employee(
    employee_id: str,
    title: str,
    body: str,
    data: dict,
    db,
) -> dict:
    """Send push notification to all registered devices for an employee."""

    # Fetch all active device tokens for this employee
    tokens = await db.execute(
        """SELECT token, type, platform FROM device_tokens
           WHERE employee_id = :eid AND is_active = TRUE""",
        {"eid": employee_id}
    )

    results = {"fcm": [], "apns": [], "web": [], "errors": []}

    fcm_tokens = []
    apns_tokens = []
    web_tokens = []

    for row in tokens:
        if row.type == "fcm":
            fcm_tokens.append(row.token)
        elif row.type == "apns":
            apns_tokens.append(row.token)
        elif row.type == "web":
            web_tokens.append(row.token)

    # ── FCM (Android + Web) ────────────────────────────────────
    if fcm_tokens:
        message = messaging.MulticastMessage(
            tokens=fcm_tokens,
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={k: str(v) for k, v in data.items()},
            android=messaging.AndroidConfig(
                priority="high",
                ttl=86400,
                notification=messaging.AndroidNotification(
                    icon="ic_notification",
                    color="#3B82F6",
                    sound="default",
                    channel_id="hrms_alerts",
                ),
            ),
        )
        response = messaging.send_each_for_multicast(message)
        results["fcm"] = [
            {"success": r.success, "error": str(r.exception) if r.exception else None}
            for r in response.responses
        ]

        # Remove invalid FCM tokens
        for i, r in enumerate(response.responses):
            if not r.success and "INVALID_REGISTRATION" in str(r.exception):
                await deactivate_device_token(fcm_tokens[i], db)

    # ── APNs (iOS via HTTP/2) ──────────────────────────────────
    if apns_tokens:
        apns_client = APNs(
            key=os.environ["APNS_KEY_PATH"],
            key_id=os.environ["APNS_KEY_ID"],
            team_id=os.environ["APNS_TEAM_ID"],
            topic="com.company.hrms",
            use_sandbox=os.environ.get("ENVIRONMENT") != "production",
        )
        for token in apns_tokens:
            request = NotificationRequest(
                device_token=token,
                message={
                    "aps": {
                        "alert": {"title": title, "body": body},
                        "badge": 1,
                        "sound": "default",
                        "content-available": 1,
                    },
                    **data,
                },
            )
            result = await apns_client.send_notification(request)
            results["apns"].append({
                "token": token[:8] + "...",
                "success": result.is_successful,
                "error": result.description if not result.is_successful else None,
            })

    return results
```

### Deep Link Handling (Notification Tap)
```typescript
// frontend/lib/push/notification-handler.ts

// Service Worker — handles background push events
self.addEventListener("push", (event: PushEvent) => {
  const data = event.data?.json();

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icons/hrms-192.png",
      badge: "/icons/badge-72.png",
      data: data.data,           // {screen: "/leave/my", request_id: "uuid"}
      actions: getNotificationActions(data.data?.type),
      vibrate: [100, 50, 100],
    })
  );
});

// Handle notification click → navigate to correct screen
self.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();
  const screen = event.notification.data?.screen || "/dashboard";

  event.waitUntil(
    clients.matchAll({ type: "window" }).then((windowClients) => {
      // Focus existing window if open
      for (const client of windowClients) {
        if ("focus" in client) {
          client.focus();
          client.postMessage({ type: "NAVIGATE", url: screen });
          return;
        }
      }
      // Open new window
      return clients.openWindow(screen);
    })
  );
});

function getNotificationActions(type?: string): NotificationAction[] {
  const actions: Record<string, NotificationAction[]> = {
    leave_pending_approval: [
      { action: "approve", title: "✅ Approve" },
      { action: "view", title: "View Details" },
    ],
    payroll_pending_approval: [
      { action: "view", title: "Review Payroll" },
    ],
    default: [],
  };
  return actions[type ?? "default"] ?? [];
}
```

---

## 14.5 Biometric Authentication Flow

```typescript
// React Native (Expo) biometric auth
// mobile/auth/biometric.ts
import * as LocalAuthentication from "expo-local-authentication";
import * as SecureStore from "expo-secure-store";

const REFRESH_TOKEN_KEY = "hrms_refresh_token";

export async function setupBiometricAuth(): Promise<{ success: boolean; error?: string }> {
  // 1. Check device support
  const hasHardware = await LocalAuthentication.hasHardwareAsync();
  const isEnrolled = await LocalAuthentication.isEnrolledAsync();
  const supportedTypes = await LocalAuthentication.supportedAuthenticationTypesAsync();

  if (!hasHardware || !isEnrolled) {
    return { success: false, error: "Biometric hardware or enrollment not available" };
  }

  // 2. Verify device has fingerprint or face ID
  const hasFaceID = supportedTypes.includes(
    LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION
  );
  const hasFingerprint = supportedTypes.includes(
    LocalAuthentication.AuthenticationType.FINGERPRINT
  );

  if (!hasFaceID && !hasFingerprint) {
    return { success: false, error: "No supported biometric type" };
  }

  // 3. Store refresh token in SecureStore (encrypted, biometric-protected)
  const refreshToken = await getRefreshToken();
  if (refreshToken) {
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
      // On iOS: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
      // On Android: EncryptedSharedPreferences with BiometricManager
    });
  }

  // 4. Save preference
  await SecureStore.setItemAsync("biometric_enabled", "true");

  return { success: true };
}


export async function authenticateWithBiometric(): Promise<{
  success: boolean;
  accessToken?: string;
  error?: string;
}> {
  const isEnabled = await SecureStore.getItemAsync("biometric_enabled");
  if (!isEnabled) {
    return { success: false, error: "Biometric not set up" };
  }

  // 1. Trigger biometric prompt
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: "Authenticate to access HRMS",
    fallbackLabel: "Use PIN instead",
    cancelLabel: "Cancel",
    disableDeviceFallback: false,
  });

  if (!result.success) {
    return { success: false, error: result.error || "Authentication failed" };
  }

  // 2. Retrieve stored refresh token (only accessible after biometric success)
  const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);

  if (!refreshToken) {
    return { success: false, error: "Session expired — please login with password" };
  }

  // 3. Exchange refresh token for new access token
  try {
    const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      // Refresh token expired — clear biometric store, force re-login
      await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
      return { success: false, error: "Session expired — please login again" };
    }

    const data = await response.json();
    return { success: true, accessToken: data.access_token };

  } catch {
    return { success: false, error: "Network error" };
  }
}
```

---

## 14.6 Performance Budgets

| Metric | Target | Measurement Tool |
|---|---|---|
| First Contentful Paint (4G) | < 1.5s | Lighthouse CI |
| Largest Contentful Paint (4G) | < 2.5s | Lighthouse CI |
| Time to Interactive (4G) | < 3.0s | Lighthouse CI |
| Time to Interactive (3G) | < 5.0s | Lighthouse CI |
| Total Bundle Size (initial JS) | < 200KB gzipped | webpack-bundle-analyzer |
| API response p95 (employees list) | < 300ms | k6 load test |
| API response p95 (payroll status) | < 500ms | k6 load test |
| Offline → Online sync time | < 5s for 10 queued items | Manual test |
| Push notification delivery | < 3s from trigger | CloudWatch |
| PWA install prompt | Lighthouse PWA score ≥ 90 | Lighthouse CI |

### Next.js Performance Config
```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",       // minimal production image

  experimental: {
    optimizePackageImports: [
      "recharts", "lucide-react", "@radix-ui/react-dialog",
    ],
  },

  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 86400,
    remotePatterns: [
      { protocol: "https", hostname: "cdn.hrms.company.com" },
    ],
  },

  // Bundle splitting for large routes (payroll, analytics)
  webpack(config) {
    config.optimization.splitChunks = {
      chunks: "all",
      cacheGroups: {
        recharts: {
          name: "recharts",
          test: /node_modules\/recharts/,
          priority: 20,
        },
        pdfjs: {
          name: "pdfjs",
          test: /node_modules\/pdfjs-dist/,
          priority: 20,
        },
      },
    };
    return config;
  },

  // HTTP headers for caching
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
        ],
      },
      {
        source: "/api/:path*",
        headers: [
          { key: "Cache-Control", value: "no-store" },
        ],
      },
    ];
  },
};
```
