import 'package:path/path.dart' as p;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

class Settings {
  String scriptUrl, token, senderSuffix;
  bool rialToToman, sendRaw;
  Settings(this.scriptUrl, this.token, this.senderSuffix, this.rialToToman, this.sendRaw);

  static Future<Settings> load() async {
    final p = await SharedPreferences.getInstance();
    return Settings(
      p.getString('url') ?? '',
      p.getString('token') ?? '',
      p.getString('sender') ?? '30009417', // matches 0983 000 9417 / +98 3000 9417
      p.getBool('toman') ?? true,
      p.getBool('raw') ?? false,
    );
  }

  Future<void> save() async {
    final p = await SharedPreferences.getInstance();
    await p.setString('url', scriptUrl.trim());
    await p.setString('token', token.trim());
    await p.setString('sender', senderSuffix.trim());
    await p.setBool('toman', rialToToman);
    await p.setBool('raw', sendRaw);
  }
}

class Tx {
  final String uid, type, description;
  final int date, amount;
  final int? balance;
  final String? raw;
  final bool sent;
  Tx(this.uid, this.date, this.type, this.amount, this.description, this.balance, this.raw, this.sent);

  Map<String, Object?> toRow({required bool sendRaw}) => {
        'uid': uid,
        'date': date,
        'type': type,
        'amount': amount,
        'description': description,
        'balance': balance ?? '',
        'ref': '',
        'raw': sendRaw ? (raw ?? '') : '',
      };
}

class Store {
  static Database? _db;

  static Future<Database> db() async => _db ??= await openDatabase(
        p.join(await getDatabasesPath(), 'moneta_phone.db'),
        version: 1,
        onCreate: (d, _) => d.execute('''
          CREATE TABLE queue (
            uid TEXT PRIMARY KEY, date INTEGER NOT NULL, type TEXT NOT NULL,
            amount INTEGER NOT NULL, description TEXT NOT NULL, balance INTEGER,
            raw TEXT, sent INTEGER NOT NULL DEFAULT 0)'''),
      );

  /// Returns true if the row was new.
  static Future<bool> insert(Tx t) async {
    final d = await db();
    final id = await d.insert(
        'queue',
        {
          'uid': t.uid, 'date': t.date, 'type': t.type, 'amount': t.amount,
          'description': t.description, 'balance': t.balance, 'raw': t.raw, 'sent': 0,
        },
        conflictAlgorithm: ConflictAlgorithm.ignore);
    return id != 0;
  }

  static Tx _tx(Map<String, Object?> r) => Tx(r['uid'] as String, r['date'] as int, r['type'] as String,
      r['amount'] as int, r['description'] as String, r['balance'] as int?, r['raw'] as String?, r['sent'] == 1);

  static Future<List<Tx>> pending({int limit = 200}) async =>
      (await (await db()).query('queue', where: 'sent = 0', orderBy: 'date', limit: limit)).map(_tx).toList();

  static Future<List<Tx>> recent({int limit = 50}) async =>
      (await (await db()).query('queue', orderBy: 'date DESC', limit: limit)).map(_tx).toList();

  static Future<void> markSent(List<String> uids) async {
    final d = await db();
    final b = d.batch();
    for (final u in uids) {
      b.update('queue', {'sent': 1}, where: 'uid = ?', whereArgs: [u]);
    }
    await b.commit(noResult: true);
  }

  static Future<int> count({required bool sent}) async => Sqflite.firstIntValue(
      await (await db()).rawQuery('SELECT COUNT(*) FROM queue WHERE sent = ?', [sent ? 1 : 0]))!;
}
