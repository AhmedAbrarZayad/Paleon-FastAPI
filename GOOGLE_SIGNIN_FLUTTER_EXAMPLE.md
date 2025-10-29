# Google Sign-In with Flutter + Backend

## **1. Flutter Setup**

### Install Supabase Flutter Package

```yaml
# pubspec.yaml
dependencies:
  supabase_flutter: ^2.0.0
  http: ^1.1.0
```

### Initialize Supabase in Flutter

```dart
// main.dart
import 'package:supabase_flutter/supabase_flutter.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  await Supabase.initialize(
    url: 'YOUR_SUPABASE_URL',
    anonKey: 'YOUR_SUPABASE_ANON_KEY',
  );
  
  runApp(MyApp());
}

final supabase = Supabase.instance.client;
```

---

## **2. Flutter Google Sign-In Code**

```dart
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class AuthService {
  final supabase = Supabase.instance.client;
  final String backendUrl = 'http://localhost:8000'; // Your backend URL
  
  /// Sign in with Google
  Future<Map<String, dynamic>> signInWithGoogle() async {
    try {
      // Step 1: Supabase handles Google OAuth
      final AuthResponse response = await supabase.auth.signInWithOAuth(
        Provider.google,
        redirectTo: 'YOUR_APP_DEEP_LINK', // e.g., 'paleon://auth-callback'
      );
      
      // Wait for auth state change
      final session = await supabase.auth.onAuthStateChange.firstWhere(
        (state) => state.session != null,
      );
      
      if (session.session == null) {
        throw Exception('Google sign-in cancelled');
      }
      
      // Step 2: Get Supabase access token
      final String supabaseAccessToken = session.session!.accessToken;
      
      // Step 3: Send token to your backend to create/get profile
      final backendResponse = await http.post(
        Uri.parse('$backendUrl/auth/oauth/signin'),
        headers: {
          'Authorization': 'Bearer $supabaseAccessToken',
          'Content-Type': 'application/json',
        },
      );
      
      if (backendResponse.statusCode == 200) {
        final data = json.decode(backendResponse.body);
        
        // Store your backend JWT token
        final String backendJwtToken = data['access_token'];
        final Map<String, dynamic> user = data['user'];
        
        // Save token for future API calls
        await _saveToken(backendJwtToken);
        
        print('✅ Signed in: ${user['email']}');
        print('Tier: ${user['tier']}');
        
        return {
          'success': true,
          'token': backendJwtToken,
          'user': user,
        };
      } else {
        throw Exception('Backend sign-in failed: ${backendResponse.body}');
      }
      
    } catch (e) {
      print('❌ Google sign-in error: $e');
      rethrow;
    }
  }
  
  /// Save token to secure storage
  Future<void> _saveToken(String token) async {
    // Use flutter_secure_storage or shared_preferences
    // Example:
    // await secureStorage.write(key: 'auth_token', value: token);
  }
  
  /// Get saved token
  Future<String?> getToken() async {
    // return await secureStorage.read(key: 'auth_token');
    return null; // Implement based on your storage choice
  }
  
  /// Sign out
  Future<void> signOut() async {
    await supabase.auth.signOut();
    // Clear saved token
    // await secureStorage.delete(key: 'auth_token');
  }
}
```

---

## **3. Flutter UI Example**

```dart
import 'package:flutter/material.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final AuthService _authService = AuthService();
  bool _isLoading = false;
  
  Future<void> _handleGoogleSignIn() async {
    setState(() => _isLoading = true);
    
    try {
      final result = await _authService.signInWithGoogle();
      
      if (result['success']) {
        // Navigate to home screen
        Navigator.pushReplacementNamed(context, '/home');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Sign-in failed: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Paleon Login')),
      body: Center(
        child: _isLoading
            ? CircularProgressIndicator()
            : ElevatedButton.icon(
                onPressed: _handleGoogleSignIn,
                icon: Icon(Icons.login),
                label: Text('Sign in with Google'),
                style: ElevatedButton.styleFrom(
                  padding: EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                ),
              ),
      ),
    );
  }
}
```

---

## **4. Making Authenticated API Calls**

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiService {
  final String backendUrl = 'http://localhost:8000';
  final AuthService _authService = AuthService();
  
  /// Upload image for classification
  Future<Map<String, dynamic>> classifyImage(String imagePath) async {
    // Get saved token
    final token = await _authService.getToken();
    
    if (token == null) {
      throw Exception('Not authenticated');
    }
    
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('$backendUrl/classify-async/'),
    );
    
    // Add authorization header
    request.headers['Authorization'] = 'Bearer $token';
    
    // Add image file
    request.files.add(await http.MultipartFile.fromPath('image_files', imagePath));
    
    // Send request
    final response = await request.send();
    final responseBody = await response.stream.bytesToString();
    
    if (response.statusCode == 200) {
      return json.decode(responseBody);
    } else if (response.statusCode == 429) {
      throw Exception('Rate limit exceeded');
    } else {
      throw Exception('Classification failed: $responseBody');
    }
  }
  
  /// Get classification result
  Future<Map<String, dynamic>> getResult(String jobId) async {
    final token = await _authService.getToken();
    
    final response = await http.get(
      Uri.parse('$backendUrl/result/$jobId'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to get result');
    }
  }
}
```

---

## **5. Complete Flow Diagram**

```
┌─────────────┐
│   Flutter   │
│     App     │
└──────┬──────┘
       │
       │ 1. User clicks "Sign in with Google"
       ▼
┌─────────────────┐
│    Supabase     │  2. Handles Google OAuth
│  Auth Service   │  3. Returns access_token + user data
└─────────┬───────┘
          │
          │ 4. Send Supabase access_token
          ▼
┌──────────────────┐
│  Your Backend    │  5. Verify token with Supabase
│  /auth/oauth/    │  6. Extract user_id (UUID)
│     signin       │  7. Create/update profile in user_profile
└─────────┬────────┘  8. Return your custom JWT token
          │
          │ 9. Flutter saves JWT token
          ▼
┌─────────────────┐
│  Authenticated  │  10. Use JWT for all API calls
│   API Calls     │      (classify-async, result, etc.)
└─────────────────┘
```

---

## **6. Important Notes**

### ✅ **Security**
- Never trust user_id from frontend directly
- Always verify Supabase token server-side
- Use your own JWT for API authentication

### ✅ **User Flow**
- First time: Creates profile in `user_profile` table
- Returning user: Just returns existing profile + new JWT

### ✅ **Rate Limiting**
- Works automatically with your tier system
- OAuth users start with FREE tier (10 requests/day)

### ✅ **Supabase Configuration Needed**
1. Enable Google provider in Supabase Dashboard
2. Add Google OAuth credentials (Client ID, Secret)
3. Set redirect URL in Google Console

---

## **7. Testing**

```bash
# Test backend endpoint directly
curl -X POST http://localhost:8000/auth/oauth/signin \
  -H "Authorization: Bearer <SUPABASE_ACCESS_TOKEN>" \
  -H "Content-Type: application/json"

# Expected response:
{
  "access_token": "eyJ...",  # Your backend JWT
  "token_type": "bearer",
  "user": {
    "user_id": "uuid-here",
    "email": "user@gmail.com",
    "name": "User Name",
    "tier": "free",
    "avatar": "https://lh3.googleusercontent.com/..."
  }
}
```

---

## **Summary**

✅ **Backend changes complete:**
- Added `create_or_update_profile_from_oauth()` in repositories
- Added `/auth/oauth/signin` endpoint
- Verifies Supabase token server-side
- Creates profile with Google user data

✅ **Flutter implementation:**
- Use `supabase_flutter` package
- Call `signInWithOAuth(Provider.google)`
- Send Supabase token to backend
- Save backend JWT for API calls

✅ **No password stored** for OAuth users
✅ **Profile synced** with Google data (name, avatar)
✅ **Rate limiting** works automatically
