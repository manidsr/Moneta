import 'dart:convert';
import 'package:http/http.dart' as http;
import 'store.dart';

/// Sends queued rows to the Apps Script web app that appends them to the sheet.
class Uploader {
  /// Returns null on success (or nothing to do), otherwise an error message.
  static Future<String?> syncPending() async {
    final s = await Settings.load();
    if (s.scriptUrl.isEmpty) return 'Script URL is not set (open Settings)';
    try {
      for (var i = 0; i < 20; i++) {
        final batch = await Store.pending(limit: 100);
        if (batch.isEmpty) return null;
        final body = jsonEncode({
          'token': s.token,
          'rows': batch.map((t) => t.toRow(sendRaw: s.sendRaw)).toList(),
        });
        final client = http.Client();
        try {
          final req = http.Request('POST', Uri.parse(s.scriptUrl))
            ..headers['Content-Type'] = 'text/plain'
            ..followRedirects = false
            ..body = body;
          var res = await http.Response.fromStream(await client.send(req).timeout(const Duration(seconds: 40)));
          // Apps Script answers a POST with a redirect to the result.
          if ({301, 302, 303, 307, 308}.contains(res.statusCode) && res.headers['location'] != null) {
            res = await client.get(Uri.parse(res.headers['location']!)).timeout(const Duration(seconds: 40));
          }
          final j = jsonDecode(utf8.decode(res.bodyBytes));
          if (j is! Map || j['ok'] != true) return 'Server said: ${j is Map ? j['error'] : res.statusCode}';
          await Store.markSent(batch.map((t) => t.uid).toList());
        } finally {
          client.close();
        }
      }
      return null;
    } catch (e) {
      return 'Upload failed (will retry): $e';
    }
  }
}
