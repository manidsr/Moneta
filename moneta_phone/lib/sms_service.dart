import 'dart:convert';
import 'package:another_telephony/telephony.dart';
import 'package:crypto/crypto.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'parser.dart';
import 'store.dart';
import 'uploader.dart';

/// Runs in a background isolate when an SMS arrives and the app is closed.
@pragma('vm:entry-point')
Future<void> backgroundSmsHandler(SmsMessage m) async {
  await SmsService.ingest(m.address, m.body, m.date);
  await Uploader.syncPending();
}

class SmsService {
  static final _t = Telephony.instance;
  static const _lastKey = 'lastScan';

  /// Parse one SMS and put it in the local queue. Returns true if it was new.
  /// Pass [settings] when calling in a loop so they are loaded only once.
  static Future<bool> ingest(String? address, String? body, int? dateMs, {Settings? settings}) async {
    if (address == null || body == null) return false;
    final s = settings ?? await Settings.load();
    final addr = digitsOnly(address);
    String? suffix;
    for (final x in s.senderSuffix.split(RegExp(r'[,;\s]+')).map(digitsOnly)) {
      if (x.isNotEmpty && addr.endsWith(x)) {
        suffix = x;
        break;
      }
    }
    if (suffix == null) return false;
    final p = parseAnySms(body);
    if (p == null) return false;

    final date = dateMs ?? DateTime.now().millisecondsSinceEpoch;
    // uses the MATCHED suffix, so uids stay identical to before (no duplicates)
    final uid = 'm${sha1.convert(utf8.encode('$suffix|$date|$body')).toString().substring(0, 32)}';
    int conv(int v) => s.rialToToman ? (v / 10).round() : v;
    final amount = conv(p.amount);
    return Store.insert(Tx(uid, date, p.type, amount < 1 ? 1 : amount, p.description,
        p.balance == null ? null : conv(p.balance!), body, false));
  }

  /// Reads only SMS newer than the last scan (first run = whole inbox, once).
  /// Duplicates are impossible: same SMS -> same uid -> ignored by the database.
  static Future<int> scanInbox({bool background = false}) async {
    if (!background) {
      final ok = await _t.requestSmsPermissions ?? false;
      if (!ok) throw 'SMS permission denied';
    }
    final prefs = await SharedPreferences.getInstance();
    final last = prefs.getInt(_lastKey) ?? 0;
    final started = DateTime.now().millisecondsSinceEpoch;
    final msgs = await _t.getInboxSms(
      columns: [SmsColumn.ADDRESS, SmsColumn.BODY, SmsColumn.DATE],
      filter: last == 0 ? null : SmsFilter.where(SmsColumn.DATE).greaterThan('${last - 86400000}'),
      sortOrder: [OrderBy(SmsColumn.DATE, sort: Sort.ASC)],
    );
    final s = await Settings.load();
    var added = 0;
    for (final m in msgs) {
      if (await ingest(m.address, m.body, m.date, settings: s)) added++;
    }
    await prefs.setInt(_lastKey, started);
    return added;
  }

  static void listen(void Function() onChange) {
    _t.listenIncomingSms(
      onNewMessage: (m) async {
        await ingest(m.address, m.body, m.date);
        await Uploader.syncPending();
        onChange();
      },
      onBackgroundMessage: backgroundSmsHandler,
      listenInBackground: true,
    );
  }
}
