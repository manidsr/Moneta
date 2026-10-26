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
    // Setting may hold several senders, e.g. "30009417, 9999987641"
    final suffixes = s.senderSuffix
        .split(RegExp(r'[,;\s]+'))
        .map(digitsOnly)
        .where((x) => x.isNotEmpty);
    final addr = digitsOnly(address);
    final suffix = suffixes.cast<String?>().firstWhere((x) => addr.endsWith(x!), orElse: () => null);
    if (suffix == null) return false;
    final p = parseAnySms(body);
    if (p == null) return false;

    final date = dateMs ?? DateTime.now().millisecondsSinceEpoch;
    // uses the MATCHED suffix, so Melli uids stay identical to before (no duplicates)
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
