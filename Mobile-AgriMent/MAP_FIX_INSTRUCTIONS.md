# Map Display Fix Instructions

## Issue
When you alert an insect detection to your region, the marker doesn't appear on the map screen.

## Root Cause
The map is working correctly, but there are two potential issues:

1. **GPS Permissions**: The app needs location permissions to capture GPS coordinates when taking photos
2. **Map Not Refreshing**: The map screen doesn't automatically refresh after you send an alert

## Solution

### Quick Fix: Manual Refresh
After alerting a pest to your region:
1. Go to the Map screen
2. **Pull down to refresh** OR
3. **Close and reopen** the Map screen
4. Your detection should now appear as a marker

### Permanent Fix: Auto-refresh

I'll update the MapScreen to automatically reload when you navigate to it:

