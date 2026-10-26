import 'dart:convert';
import 'package:another_telephony/telephony.dart';
import 'package:crypto/crypto.dart';
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

  /// Parse one SMS and put it in the local queue. Returns true if it was new.
  static Future<bool> ingest(String? address, String? body, int? dateMs) async {
    if (address == null || body == null) return false;
    final s = await Settings.load();
    final suffix = digitsOnly(s.senderSuffix);
    if (suffix.isEmpty || !digitsOnly(address).endsWith(suffix)) return false;
    final p = parseBankSms(body);
    if (p == null) return false;

    final date = dateMs ?? DateTime.now().millisecondsSinceEpoch;
    // Same SMS -> same uid, always. Leading letter stops Sheets reading it as a number.
    final uid = 'm${sha1.convert(utf8.encode('$suffix|$date|$body')).toString().substring(0, 32)}';
    int conv(int v) => s.rialToToman ? (v / 10).round() : v;
    final amount = conv(p.amount);
    return Store.insert(Tx(uid, date, p.type, amount < 1 ? 1 : amount, p.description,
        p.balance == null ? null : conv(p.balance!), body, false));
  }

  /// Read the whole inbox, queue every matching SMS. Returns number of NEW rows.
  static Future<int> scanInbox() async {
    final ok = await _t.requestSmsPermissions ?? false;
    if (!ok) throw 'SMS permission denied';
    final msgs = await _t.getInboxSms(
      columns: [SmsColumn.ADDRESS, SmsColumn.BODY, SmsColumn.DATE],
      sortOrder: [OrderBy(SmsColumn.DATE, sort: Sort.ASC)],
    );
    var added = 0;
    for (final m in msgs) {
      if (await ingest(m.address, m.body, m.date)) added++;
    }
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
